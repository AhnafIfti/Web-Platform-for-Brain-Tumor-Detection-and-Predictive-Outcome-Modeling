import gzip
import tempfile
from pathlib import Path
from unittest.mock import patch
import nibabel as nib
import numpy as np
import torch
from django.test import SimpleTestCase, override_settings
from analysis.services.errors import InvalidMRI, ModelUnavailable, AnalysisError
from analysis.services.nifti_utils import load_pair, load_volume
from analysis.services.preprocessing import normalize_slice, prepare_slice
from analysis.services.inference import infer_probabilities
from analysis.services import model_loader
from ml_models.model_definition import build_model


class PreprocessingTests(SimpleTestCase):
    def test_notebook_normalization(self):
        array = np.array([[0, 2], [4, 8]], dtype=np.float64)
        np.testing.assert_array_equal(normalize_slice(array), array.astype(np.float32) / 8)

    def test_constant_positive_guard(self):
        np.testing.assert_array_equal(normalize_slice(np.full((3, 3), 8.0)), np.zeros((3, 3)))

    def test_nonpositive_is_preserved(self):
        array = np.array([[-4, -2], [-1, 0]])
        np.testing.assert_array_equal(normalize_slice(array), array)

    def test_channel_order_resize_and_shape(self):
        a = np.arange(36, dtype=np.float64).reshape(6, 6)
        b = a.T
        actual = prepare_slice(a, b)
        expected = torch.nn.functional.interpolate(torch.tensor(np.stack([a / 35, b / 35]), dtype=torch.float32)[None],
                                                   size=(224, 224), mode='bilinear', align_corners=False)
        self.assertEqual(tuple(actual.shape), (1, 2, 224, 224))
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)


class NiftiTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def volume(self, name, shape=(6, 6, 4), affine=None, data=None):
        path = self.root / name
        data = np.ones(shape, dtype=np.float32) if data is None else data
        nib.save(nib.Nifti1Image(data, np.eye(4) if affine is None else affine), path)
        return path

    def test_valid_nii_and_gz(self):
        image, a, b = load_pair(self.volume('f.nii'), self.volume('t.nii.gz'))
        self.assertEqual(a.shape, (6, 6, 4))
        np.testing.assert_array_equal(a, b)

    def test_mismatched_shape(self):
        with self.assertRaisesMessage(InvalidMRI, 'dimensions'):
            load_pair(self.volume('f.nii'), self.volume('t.nii', shape=(5, 6, 4)))

    def test_mismatched_affine(self):
        affine = np.eye(4); affine[0, 3] = 10
        with self.assertRaisesMessage(InvalidMRI, 'spatial transforms'):
            load_pair(self.volume('f.nii'), self.volume('t.nii', affine=affine))

    def test_corrupt(self):
        path = self.root / 'bad.nii'; path.write_bytes(b'not a volume')
        with self.assertRaises(InvalidMRI):
            load_volume(path)

    def test_4d_rejected(self):
        with self.assertRaises(InvalidMRI):
            load_volume(self.volume('4d.nii', shape=(3, 3, 3, 2)))

    def test_nan_rejected(self):
        data = np.ones((4, 4, 4), dtype=np.float32); data[0, 0, 0] = np.nan
        with self.assertRaises(InvalidMRI):
            load_volume(self.volume('nan.nii', data=data))

    @override_settings(MAX_UNCOMPRESSED_MRI_MB=1)
    def test_decompression_limit(self):
        path = self.root / 'bomb.nii.gz'
        with gzip.open(path, 'wb') as stream:
            stream.write(b'0' * (2 * 1024 * 1024))
        with self.assertRaisesMessage(InvalidMRI, 'expanded'):
            load_volume(path)

    @override_settings(MAX_VOLUME_VOXELS=8)
    def test_header_dimension_limit(self):
        with self.assertRaises(InvalidMRI):
            load_volume(self.volume('large.nii'))


class ModelTests(SimpleTestCase):
    def setUp(self):
        self.previous = model_loader._loaded
        model_loader._loaded = None
        self.addCleanup(setattr, model_loader, '_loaded', self.previous)

    def test_missing_checkpoint(self):
        with override_settings(MODEL_CHECKPOINT_PATH=Path('does-not-exist.pth')):
            with self.assertRaises(ModelUnavailable):
                model_loader.get_model()

    def test_real_architecture_output_contract(self):
        # Structural test only: random weights are never used by the application.
        torch.set_num_threads(2)
        model = build_model().eval()
        probabilities = infer_probabilities(model, torch.zeros((1, 2, 224, 224)), torch.device('cpu'))
        self.assertEqual(probabilities.shape, (3, 224, 224))
        self.assertTrue(np.isfinite(probabilities).all())
        self.assertTrue(((probabilities >= 0) & (probabilities <= 1)).all())

    def test_strict_state_dict_and_singleton(self):
        # Small real PyTorch module isolates serialization behavior; test-only patch.
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'weights.pth'
            layer = torch.nn.Linear(2, 3)
            torch.save({'model_state_dict': layer.state_dict()}, path)
            with override_settings(MODEL_CHECKPOINT_PATH=path, MODEL_DEVICE='cpu'):
                with patch.object(model_loader, 'build_model', return_value=torch.nn.Linear(2, 3)) as builder:
                    first = model_loader.get_model()
                    self.assertIs(first, model_loader.get_model())
                    self.assertEqual(builder.call_count, 1)
                    self.assertFalse(first[0].training)
                    self.assertEqual(len(first[2]), 64)
                    torch.testing.assert_close(first[0].weight, layer.weight)

    def test_incompatible_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'wrong.pth'; torch.save({'wrong': torch.zeros(1)}, path)
            with override_settings(MODEL_CHECKPOINT_PATH=path):
                with patch.object(model_loader, 'build_model', return_value=torch.nn.Linear(2, 3)):
                    with self.assertRaises(ModelUnavailable):
                        model_loader.get_model()

    def test_wrong_prediction_shape_rejected(self):
        with self.assertRaises(AnalysisError):
            infer_probabilities(torch.nn.Identity(), torch.zeros(1, 2, 224, 224), torch.device('cpu'))
