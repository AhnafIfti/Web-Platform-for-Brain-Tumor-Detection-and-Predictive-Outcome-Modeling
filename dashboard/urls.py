from django.urls import path
from . import views
urlpatterns = [path('dashboard/', views.overview, name='dashboard'), path('research/', views.research, name='research'),
               path('settings/', views.preferences, name='settings')]
