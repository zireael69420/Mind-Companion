from django import views
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('wellness.urls')),
    path('profile/clear-history/', views.clear_watch_history, name='clear_watch_history'),
]
