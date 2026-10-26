import tempfile
from pathlib import Path
from unittest.mock import patch
import nibabel as nib
import numpy as np
import torch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from analysis.models import MRIAnalysis
from analysis.services.inference import process_analysis
from analysis.services.visualization import result_dir
from performance.services import read_benchmarks


@override_settings(STORAGES={'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class WebTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.checkpoint = self.root / 'configured.pth'
        self.checkpoint.write_bytes(b'test-only presence marker; never loaded')
        self.settings_override = override_settings(MEDIA_ROOT=self.root / 'media', MODEL_CHECKPOINT_PATH=self.checkpoint)
        self.settings_override.enable(); self.addCleanup(self.settings_override.disable)
        self.user = get_user_model().objects.create_user('researcher', password='test-password')
        self.client.force_login(self.user)

    def file(self, name='scan.nii', shape=(8, 8, 3)):
        image = nib.Nifti1Image(np.arange(np.prod(shape), dtype=np.float32).reshape(shape), np.eye(4))
        return SimpleUploadedFile(name, image.to_bytes(), content_type='application/octet-stream')

    def upload(self, **kwargs):
        values = {'flair_file': self.file(), 't1ce_file': self.file('t1.nii'), 'research_consent': 'on'}
        values.update(kwargs)
        return self.client.post('/api/analysis/', values)

    def test_create_private_record(self):
        response = self.upload()
        self.assertEqual(response.status_code, 202, response.content)
        record = MRIAnalysis.objects.get()
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.status, 'queued')
        self.assertNotIn('scan.nii', record.flair_file.name)
        self.assertNotIn(str(self.root), response.content.decode())

    def test_unsupported_extension(self):
        response = self.upload(flair_file=SimpleUploadedFile('scan.jpg', b'jpeg'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MRIAnalysis.objects.count(), 0)

    def test_corrupted_volume_and_cleanup(self):
        response = self.upload(flair_file=SimpleUploadedFile('scan.nii', b'corrupt'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(MRIAnalysis.objects.count(), 0)
        self.assertFalse(list((self.root / 'media').rglob('*.nii')))

    def test_mismatched_pair(self):
        response = self.upload(t1ce_file=self.file('t1.nii', (7, 8, 3)))
        self.assertEqual(response.status_code, 400)
        self.assertIn('dimensions', response.json()['error'])

    def test_missing_model_clear_error(self):
        with override_settings(MODEL_CHECKPOINT_PATH=self.root / 'missing.pth'):
            response = self.upload()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(MRIAnalysis.objects.count(), 0)

    def test_consent_required(self):
        self.assertEqual(self.upload(research_consent='').status_code, 400)

    def test_anonymous_access(self):
        self.client.logout()
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)
        self.assertEqual(self.client.post('/api/analysis/').status_code, 401)

    def test_other_user_cannot_access(self):
        self.upload()
        record = MRIAnalysis.objects.get()
        other = get_user_model().objects.create_user('other')
        self.client.force_login(other)
        for url in [f'/analysis/{record.id}/', f'/api/analysis/{record.id}/',
                    f'/analysis/{record.id}/slice/0/original/', f'/analysis/{record.id}/report/']:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(f'/analysis/{record.id}/delete/').status_code, 404)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/api/analysis/').status_code, 403)

    def test_all_pages_render(self):
        for url in ['/dashboard/', '/analysis/new/', '/history/', '/performance/', '/research/', '/settings/', '/accounts/password/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertContains(response, 'NeuroVision')

    def test_registration_disabled(self):
        self.assertEqual(self.client.get('/register/').status_code, 404)

    def test_active_queue_limit(self):
        self.assertEqual(self.upload().status_code, 202)
        self.assertEqual(self.upload().status_code, 202)
        self.assertEqual(self.upload().status_code, 400)
        self.assertEqual(MRIAnalysis.objects.count(), 2)

    @override_settings(MAX_UPLOAD_SIZE_MB=1)
    def test_streaming_upload_size_limit(self):
        response = self.upload(flair_file=SimpleUploadedFile('large.nii', b'0' * (2 * 1024 * 1024)))
        self.assertEqual(response.status_code, 413)

    def test_worker_failure_persisted(self):
        self.upload()
        record = MRIAnalysis.objects.get()
        with override_settings(MODEL_CHECKPOINT_PATH=self.root / 'missing.pth'):
            process_analysis(record)
        record.refresh_from_db()
        self.assertEqual(record.status, 'failed')
        self.assertIn('Model unavailable', record.error_message)
        self.assertEqual(self.client.get(f'/analysis/{record.id}/').status_code, 200)

    def test_pipeline_artifacts_report_and_deletion(self):
        # Test-only network checks plumbing; it is never an application fallback.
        self.upload(); record = MRIAnalysis.objects.get()
        network = torch.nn.Conv2d(2, 3, 1).eval()
        with patch('analysis.services.inference.get_model', return_value=(network, torch.device('cpu'), '0' * 64)):
            process_analysis(record)
        record.refresh_from_db()
        self.assertEqual(record.status, 'completed')
        self.assertEqual(len(record.result_metadata['slices']), 3)
        self.assertTrue((result_dir(record.id) / '0-probabilities.npy').is_file())
        self.assertEqual(np.load(result_dir(record.id) / '0-masks.npy').shape, (3, 224, 224))
        self.assertEqual(self.client.get(f'/analysis/{record.id}/').status_code, 200)
        image = self.client.get(f'/analysis/{record.id}/slice/0/wt/')
        self.assertEqual(image.status_code, 200)
        self.assertTrue(b''.join(image.streaming_content).startswith(b'\x89PNG'))
        report = self.client.get(f'/analysis/{record.id}/report/')
        self.assertEqual(report.status_code, 200)
        content = b''.join(report.streaming_content)
        self.assertTrue(content.startswith(b'%PDF'))
        self.assertIn('attachment;', report['Content-Disposition'])
        import base64
        export = self.client.get(f'/analysis/{record.id}/report/', HTTP_ACCEPT='application/json')
        self.assertEqual(export.status_code, 200)
        self.assertTrue(base64.b64decode(export.json()['content']).startswith(b'%PDF'))
        self.assertTrue(export.json()['filename'].endswith('-analysis-summary.pdf'))
        self.assertEqual(export['Cache-Control'], 'private, no-store')
        preview = self.client.get(f'/analysis/{record.id}/report/?inline=1')
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview['Content-Type'], 'application/pdf')
        self.assertIn('inline;', preview['Content-Disposition'])
        self.assertTrue(b''.join(preview.streaming_content).startswith(b'%PDF'))
        self.assertEqual(self.client.get(f'/analysis/{record.id}/slice/10/wt/').status_code, 404)
        self.assertEqual(self.client.get(f'/analysis/{record.id}/slice/0/secrets/').status_code, 404)
        record_id = record.id
        self.assertEqual(self.client.post(f'/analysis/{record.id}/delete/').status_code, 302)
        self.assertEqual(MRIAnalysis.objects.count(), 0)
        self.assertFalse(result_dir(record_id).exists())

    def test_benchmarks_are_recorded_and_not_v2(self):
        rows, error = read_benchmarks()
        self.assertFalse(error)
        self.assertEqual(len(rows), 18)
        self.assertEqual({r['Dataset'] for r in rows}, {'BraTS2020', 'BraTS2021'})
        self.assertFalse(any('Model v2' in r['Model'] for r in rows))

    def test_nonfinite_metric_rejected(self):
        csv = self.root / 'bad.csv'
        csv.write_text('Model,Dataset,Dice_WT,Dice_TC,Dice_ET,Avg_Dice\nA,B,nan,0.5,0.5,0.5\n')
        with override_settings(BENCHMARK_CSV=csv):
            rows, error = read_benchmarks()
        self.assertEqual(rows, [])
        self.assertTrue(error)
