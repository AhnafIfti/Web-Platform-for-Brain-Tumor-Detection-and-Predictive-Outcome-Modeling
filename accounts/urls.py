from django.contrib.auth import views
from django.urls import path
from .views import register
from .two_factor import TwoFactorLoginView, challenge, security
urlpatterns = [
    path('accounts/two-factor/', security, name='two-factor-settings'),
    path('accounts/two-factor/verify/', challenge, name='two-factor-challenge'),path('login/', TwoFactorLoginView.as_view(), name='login'),
               path('logout/', views.LogoutView.as_view(), name='logout'),
               path('register/', register, name='register'),
               path('accounts/password/', views.PasswordChangeView.as_view(template_name='registration/password.html', success_url='/settings/'), name='password-change')]
