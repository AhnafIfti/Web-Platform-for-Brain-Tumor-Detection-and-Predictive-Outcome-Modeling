import base64
import secrets
import time
from io import BytesIO
import qrcode
import django_otp
from django.contrib.auth import get_user_model, login
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils.crypto import constant_time_compare
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import RecoveryCodes


def destination(request, value):
    return value if url_has_allowed_host_and_scheme(value, {request.get_host()}, require_https=request.is_secure()) else '/dashboard/'


class TwoFactorLoginView(LoginView):
    def form_valid(self, form):
        user = form.get_user()
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            self.request.session.cycle_key()
            self.request.session['otp_pending'] = {'user': user.pk, 'backend': user.backend,
                'time': time.time(), 'hash': user.get_session_auth_hash(), 'next': self.get_success_url()}
            return redirect('two-factor-challenge')
        return super().form_valid(form)


def verify(user, token, recovery=True):
    # Serialize verification, recovery consumption and throttling per device.
    with transaction.atomic():
        device = TOTPDevice.objects.select_for_update().filter(user=user, confirmed=True).first()
        if not device or not device.verify_is_allowed()[0]:
            return None
        if recovery:
            codes = RecoveryCodes.objects.select_for_update().filter(user=user).first()
            normalized = token.strip().upper()
            if codes:
                for hashed in codes.hashes:
                    if check_password(normalized, hashed):
                        codes.hashes.remove(hashed)
                        codes.save(update_fields=['hashes'])
                        device.throttle_reset()
                        return device
        return device if device.verify_token(token.strip()) else None


@never_cache
@sensitive_post_parameters('code')
def challenge(request):
    pending = request.session.get('otp_pending', {})
    user = get_user_model().objects.filter(pk=pending.get('user'), is_active=True).first()
    if not user or time.time() - pending.get('time', 0) > 300 or not constant_time_compare(pending.get('hash', ''), user.get_session_auth_hash()):
        request.session.pop('otp_pending', None)
        return redirect('login')
    error = ''
    if request.method == 'POST':
        device = verify(user, request.POST.get('code', ''))
        if device:
            request.session.pop('otp_pending', None)
            login(request, user, backend=pending['backend'])
            django_otp.login(request, device)
            return redirect(destination(request, pending.get('next')))
        error = 'Code not accepted. Use a fresh code, or wait before trying again.'
    return render(request, 'registration/two_factor.html', {'challenge': True, 'error': error})


@login_required
@never_cache
@sensitive_post_parameters('password', 'code')
def security(request):
    active = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    context = {'enabled': bool(active)}
    if request.method == 'POST':
        action = request.POST.get('action')
        if not request.user.check_password(request.POST.get('password', '')):
            context['error'] = 'Enter your current password to change two-factor authentication.'
        elif action == 'start' and not active:
            TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()
            device = TOTPDevice.objects.create(user=request.user, name='NeuroVision AI', confirmed=False)
            request.session['otp_setup'] = {'device': device.pk, 'time': time.time()}
        elif action == 'confirm' and not active:
            pending = request.session.get('otp_setup', {})
            with transaction.atomic():
                device = TOTPDevice.objects.select_for_update().filter(pk=pending.get('device'), user=request.user, confirmed=False).first()
                if device and time.time() - pending.get('time', 0) < 600 and device.verify_token(request.POST.get('code', '')):
                    device.confirmed = True
                    device.save(update_fields=['confirmed'])
                    django_otp.login(request, device)
                    codes = [secrets.token_hex(8).upper() for _ in range(8)]
                    RecoveryCodes.objects.update_or_create(user=request.user, defaults={'hashes': [make_password(c) for c in codes]})
                    context.update(enabled=True, codes=codes)
                    active = device
                    request.session.pop('otp_setup', None)
                else:
                    context['error'] = 'Code not accepted or setup expired. Wait for a fresh code or start again.'
        elif action == 'disable' and active:
            if verify(request.user, request.POST.get('code', '')):
                TOTPDevice.objects.filter(user=request.user).delete()
                RecoveryCodes.objects.filter(user=request.user).delete()
                request.session.pop('otp_device_id', None)
                return redirect('two-factor-settings')
            context['error'] = 'Code not accepted. Use a fresh code, or wait before trying again.'
    pending = request.session.get('otp_setup', {})
    if not active and time.time() - pending.get('time', 0) < 600:
        device = TOTPDevice.objects.filter(pk=pending.get('device'), user=request.user, confirmed=False).first()
        if device:
            image = qrcode.make(device.config_url)
            output = BytesIO(); image.save(output, format='PNG')
            context.update(qr=base64.b64encode(output.getvalue()).decode(), secret=device.key)
            # Authenticator manual-entry secrets use Base32, not the DB hex encoding.
            context['secret'] = base64.b32encode(device.bin_key).decode()
    return render(request, 'registration/two_factor.html', context)
