from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard', permanent=False)),
    path('admin/', admin.site.urls), path('', include('accounts.urls')),
    path('', include('dashboard.urls')), path('', include('analysis.urls')),
    path('performance/', include('performance.urls')),
]
