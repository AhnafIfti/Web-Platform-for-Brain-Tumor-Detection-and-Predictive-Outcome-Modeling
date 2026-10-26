from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django_otp.plugins.otp_totp.models import TOTPDevice


class RequireSecondFactor:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Route admin sign-in through the same password + OTP flow.
        if request.path == '/admin/login/':
            return redirect_to_login(request.GET.get('next', '/admin/'))
        if request.user.is_authenticated and not request.user.is_verified():
            if TOTPDevice.objects.filter(user=request.user, confirmed=True).exists():
                logout(request)
                return redirect_to_login(request.get_full_path())
        return self.get_response(request)
