from django.urls import path
from . import views

app_name = 'wellness'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('recommendations/<str:emotion>/', views.recommendations, name='recommendations'),
    path('rate/', views.submit_rating, name='submit_rating'),
    path('thank-you/', views.thank_you, name='thank_you'),
]
