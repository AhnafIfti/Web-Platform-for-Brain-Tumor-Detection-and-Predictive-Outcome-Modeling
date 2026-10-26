"""Local visual QA. Uses actual empty workspace, no fabricated patient data."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def main():
    import secrets
    access = ROOT / '.local-access.txt'
    if not access.exists():
        username = 'researcher'
        if get_user_model().objects.filter(username=username).exists():
            raise RuntimeError('Existing researcher account: do not overwrite credentials.')
        password = secrets.token_urlsafe(18)
        get_user_model().objects.create_user(username, password=password)
        access.write_text(f'Local development access only\nURL: http://127.0.0.1:9130/\nUsername: {username}\nPassword: {password}\n', encoding='utf-8')
    lines = access.read_text().splitlines()
    username = next(s.split(': ', 1)[1] for s in lines if s.startswith('Username:'))
    password = next(s.split(': ', 1)[1] for s in lines if s.startswith('Password:'))
    screenshots = ROOT / 'docs/screenshots'
    screenshots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:9130/login/')
        page.fill('#id_username', username); page.fill('#id_password', password)
        page.get_by_role('button', name='Sign in', exact=False).click()
        page.wait_for_url('**/dashboard/')
        page.screenshot(path=str(screenshots / 'dashboard-desktop.png'), full_page=True)
        for url, name in [('analysis/new/', 'upload-desktop'), ('performance/', 'performance-desktop'),
                          ('history/', 'history-desktop'), ('research/', 'research-desktop'), ('settings/', 'settings-desktop')]:
            response = page.goto('http://127.0.0.1:9130/' + url)
            assert response.status == 200, (url, response.status)
            page.screenshot(path=str(screenshots / f'{name}.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow: {url}'
        page.goto('http://127.0.0.1:9130/performance/')
        page.select_option('select[name=dataset]', 'BraTS2021'); page.get_by_role('button', name='Apply filters').click()
        assert page.locator('.benchmark-table tbody tr').count() == 9
        page.goto('http://127.0.0.1:9130/analysis/new/')
        page.set_input_files('#flair-file', {'name': 'invalid.jpg', 'mimeType': 'image/jpeg', 'buffer': b'test'})
        assert page.locator('#upload-error').is_visible()
        from django.conf import settings
        assert page.locator('#run-button').is_disabled() == (not settings.MODEL_CHECKPOINT_PATH.is_file())
        for width, suffix in [(768, 'tablet'), (390, 'mobile')]:
            page.set_viewport_size({'width': width, 'height': 844})
            for url in ['dashboard/', 'analysis/new/', 'research/', 'settings/', 'performance/']:
                page.goto('http://127.0.0.1:9130/' + url)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow: {url} {width}'
            page.goto('http://127.0.0.1:9130/dashboard/')
            page.screenshot(path=str(screenshots / f'dashboard-{suffix}.png'), full_page=True)
        page.get_by_role('button', name='Toggle navigation').click()
        assert page.locator('#sidebar').evaluate("e => e.classList.contains('open')")
        assert not errors, errors
        print('Browser checks passed: login, six pages, benchmark filter, invalid upload, missing-model state, desktop/tablet/mobile overflow, navigation; no JavaScript errors.')
        browser.close()


if __name__ == '__main__':
    main()
