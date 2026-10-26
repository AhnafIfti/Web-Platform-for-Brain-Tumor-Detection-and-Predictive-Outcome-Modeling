"""Opt-in isolated UI integration test. Never writes synthetic scans to the real DB."""
import os
import tempfile
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch
import nibabel as nib
import numpy as np
import torch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings
from analysis.models import MRIAnalysis
from analysis.services.inference import process_analysis
from analysis.services.reports import create_report


@skipUnless(os.getenv('RUN_BROWSER_TESTS') == '1', 'Opt-in: RUN_BROWSER_TESTS=1 and playwright/Chrome required')
class ViewerBrowserTests(StaticLiveServerTestCase):
    def test_viewer_controls_and_report(self):
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as temp:
            with override_settings(MEDIA_ROOT=Path(temp), MODEL_VERSION='TEST-FIXTURE-NOT-TRAINED'):
                user = get_user_model().objects.create_user('browser_test', password='isolated-test-only')
                array = np.linspace(0, 1, 32 * 32 * 4, dtype=np.float32).reshape(32, 32, 4)
                path = Path(temp) / 'fixture.nii'
                nib.save(nib.Nifti1Image(array, np.eye(4)), path)
                record = MRIAnalysis.objects.create(user=user, flair_file=str(path), t1ce_file=str(path), model_version='TEST-FIXTURE-NOT-TRAINED')
                network = torch.nn.Conv2d(2, 3, 1).eval()
                with patch('analysis.services.inference.get_model', return_value=(network, torch.device('cpu'), '0' * 64)):
                    process_analysis(record)
                record.refresh_from_db()
                self.assertEqual(record.status, 'completed')
                for z in range(4):
                    for kind in ('original', 'wt', 'tc', 'et'):
                        self.assertTrue((Path(temp) / 'results' / str(record.id) / f'{z}-{kind}.png').is_file())
                output = settings.BASE_DIR / 'tmp/visual-qa'
                output.mkdir(parents=True, exist_ok=True)
                report = create_report(record)
                (output / 'TEST-ONLY-report.pdf').write_bytes(report.read())
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(channel='chrome', headless=True)
                    page = browser.new_page(viewport={'width': 1440, 'height': 1080}, accept_downloads=True)
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(self.live_server_url + '/login/')
                    page.fill('#id_username', 'browser_test'); page.fill('#id_password', 'isolated-test-only')
                    page.get_by_role('button', name='Sign in', exact=False).click()
                    page.wait_for_url('**/dashboard/')
                    page.goto(self.live_server_url + f'/analysis/{record.id}/')
                    page.wait_for_selector('#viewer-loading', state='hidden')
                    page.locator('#slice-range').fill('0'); page.locator('#slice-range').dispatch_event('input')
                    page.wait_for_selector('#viewer-loading', state='hidden')
                    self.assertEqual(page.locator('#slice-label').inner_text(), '1 / 4')
                    page.locator('#next-slice').click()
                    page.wait_for_selector('#viewer-loading', state='hidden')
                    self.assertEqual(page.locator('#slice-label').inner_text(), '2 / 4')
                    page.locator('h1').click(); page.keyboard.press('ArrowRight')
                    page.wait_for_selector('#viewer-loading', state='hidden')
                    self.assertEqual(page.locator('#slice-label').inner_text(), '3 / 4')
                    page.locator('[data-mode=mask]').click(); page.locator('[data-region=wt]').uncheck()
                    page.locator('#opacity').fill('35'); page.locator('#opacity').dispatch_event('input')
                    self.assertEqual(page.locator('#opacity-label').inner_text(), '35%')
                    self.assertTrue(page.locator('#original-canvas').is_visible())
                    for selector in ['#original-canvas', '#mri-canvas']:
                        box=page.locator(selector).bounding_box()
                        self.assertAlmostEqual(box['width'], box['height'], delta=1)
                    page.locator('#fullscreen').click()
                    page.wait_for_function('document.fullscreenElement !== null')
                    page.locator('#fullscreen').click()
                    page.wait_for_function('document.fullscreenElement === null')
                    page.locator('#zoom-in').click()
                    self.assertEqual(page.locator('#zoom-label').inner_text(), '125%')
                    self.assertEqual(page.locator('#original-canvas').get_attribute('style'), page.locator('#mri-canvas').get_attribute('style'))
                    with page.expect_download(timeout=30000) as summary:
                        page.locator('#download-report').click()
                    self.assertTrue(summary.value.suggested_filename.endswith('-analysis-summary.pdf'))
                    self.assertTrue(Path(summary.value.path()).read_bytes().startswith(b'%PDF'))
                    page.locator('#reset').click(); page.wait_for_selector('#viewer-loading', state='hidden')
                    with page.expect_download() as download:
                        page.locator('#download-image').click()
                    self.assertTrue(download.value.suggested_filename.endswith('.png'))
                    page.locator('#area-chart').click(position={'x': 49, 'y': 60})
                    page.wait_for_selector('#viewer-loading', state='hidden')
                    self.assertEqual(page.locator('#slice-label').inner_text(), '1 / 4')
                    page.evaluate("document.querySelector('h1').textContent='TEST FIXTURE · NOT A MODEL RESULT'")
                    page.screenshot(path=str(output / 'TEST-ONLY-viewer.png'), full_page=True)
                    for width in (768, 390):
                        page.set_viewport_size({'width': width, 'height': 844})
                        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    self.assertFalse(errors, errors)
                    browser.close()
