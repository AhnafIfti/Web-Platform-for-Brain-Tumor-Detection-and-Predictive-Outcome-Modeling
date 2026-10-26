import os
os.environ.setdefault('DEBUG', 'true')
from .settings import *  # noqa: F403
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
if os.getenv('RUN_BROWSER_TESTS') == '1':
    # LiveServer's shared in-memory connection is unsafe for simultaneous image requests.
    # A dedicated test file gives each request its own SQLite connection.
    (BASE_DIR / 'tmp').mkdir(exist_ok=True)
    DATABASES['default']['TEST'] = {'NAME': str(BASE_DIR / 'tmp' / f'browser-tests-{os.getpid()}.sqlite3')}
