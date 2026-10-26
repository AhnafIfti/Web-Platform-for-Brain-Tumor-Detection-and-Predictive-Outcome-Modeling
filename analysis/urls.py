from django.urls import path
from . import views
urlpatterns = [
    path('analysis/new/', views.new_analysis, name='analysis-new'),
    path('api/analysis/', views.create_analysis, name='analysis-create'),
    path('analysis/<uuid:pk>/', views.detail, name='analysis-detail'),
    path('api/analysis/<uuid:pk>/', views.status, name='analysis-status'),
    path('analysis/<uuid:pk>/slice/<int:z>/<str:kind>/', views.asset, name='analysis-asset'),
    path('analysis/<uuid:pk>/report/', views.report, name='analysis-report'),
    path('analysis/<uuid:pk>/delete/', views.delete_analysis, name='analysis-delete'),
    path('history/', views.history, name='history'),
]
