import time
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import RecoveryCodes
from .two_factor import verify


class TwoFactorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('otpuser', password='test-password')

    def enroll(self):
        return TOTPDevice.objects.create(user=self.user, confirmed=True)

    def password_login(self, **extra):
        return self.client.post('/login/', {'username':'otpuser','password':'test-password', **extra})

    def test_password_alone_does_not_authenticate_enrolled_user(self):
        device = self.enroll()
        self.assertRedirects(self.password_login(), '/accounts/two-factor/verify/')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)
        response = self.client.post('/accounts/two-factor/verify/', {'code':f'{totp(device.bin_key):06d}'})
        self.assertRedirects(response, '/dashboard/')
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)
        self.assertIsNone(verify(self.user, f'{totp(device.bin_key):06d}'))

    def test_existing_unverified_session_and_admin_cannot_bypass(self):
        self.client.force_login(self.user)
        self.enroll()
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.get('/admin/login/'), '/login/?next=/admin/')

    def test_recovery_code_consumed_and_throttled(self):
        device = self.enroll()
        RecoveryCodes.objects.create(user=self.user, hashes=[make_password('ABCDEF1234567890')])
        self.assertIsNotNone(verify(self.user, 'abcdef1234567890'))
        self.assertEqual(RecoveryCodes.objects.get(user=self.user).hashes, [])
        self.assertIsNone(verify(self.user, 'ABCDEF1234567890'))
        device.refresh_from_db()
        self.assertFalse(device.verify_is_allowed()[0])
        self.assertIsNone(verify(self.user, f'{totp(device.bin_key):06d}'))

    def test_expired_challenge_and_password_change(self):
        self.enroll(); self.password_login()
        session=self.client.session; pending=session['otp_pending'];pending['time']=time.time()-301
        session['otp_pending']=pending;session.save()
        self.assertRedirects(self.client.get('/accounts/two-factor/verify/'), '/login/')
        self.password_login();self.user.set_password('changed-password');self.user.save()
        self.assertRedirects(self.client.get('/accounts/two-factor/verify/'), '/login/')

    def test_external_next_rejected(self):
        device=self.enroll();self.password_login(next='https://evil.example/')
        self.assertRedirects(self.client.post('/accounts/two-factor/verify/', {'code':f'{totp(device.bin_key):06d}'}), '/dashboard/')

    def test_setup_confirm_recovery_and_disable(self):
        self.client.force_login(self.user)
        url='/accounts/two-factor/'
        self.client.post(url, {'action':'start','password':'wrong'})
        self.assertFalse(TOTPDevice.objects.exists())
        response=self.client.post(url, {'action':'start','password':'test-password'})
        self.assertContains(response, 'data:image/png;base64,')
        self.assertIn('no-store',response['Cache-Control'])
        device=TOTPDevice.objects.get();self.assertFalse(device.confirmed)
        response=self.client.post(url, {'action':'confirm','password':'test-password','code':f'{totp(device.bin_key):06d}'})
        self.assertContains(response, 'Two-factor authentication is on')
        codes=response.context['codes'];self.assertEqual(len(codes),8)
        self.assertNotIn(codes[0], RecoveryCodes.objects.get().hashes)
        self.assertNotContains(self.client.get(url), codes[0])
        self.assertEqual(self.client.get('/dashboard/').status_code,200)
        self.client.post(url, {'action':'disable','password':'wrong','code':codes[0]})
        self.assertTrue(TOTPDevice.objects.filter(confirmed=True).exists())
        self.assertRedirects(self.client.post(url, {'action':'disable','password':'test-password','code':codes[0]}),url)
        self.assertFalse(TOTPDevice.objects.exists())
        self.assertFalse(RecoveryCodes.objects.exists())

    def test_unenrolled_account_keeps_existing_login(self):
        self.assertRedirects(self.password_login(),'/dashboard/')
