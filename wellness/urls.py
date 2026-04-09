# wellness/urls.py

from django.urls import path
from . import views

app_name = 'wellness'

urlpatterns = [
    # Landing page
    path('', views.landing, name='landing'),

    # Auth
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # AJAX: receive emotion from landing page fetch() call
    path('select-emotion/', views.select_emotion, name='select_emotion'),

    # Recommendation page (GET or POST redirect target)
    path('recommendations/<str:emotion>/', views.recommendations, name='recommendations'),

    # AJAX: save star rating
    path('rate/', views.submit_rating, name='submit_rating'),

    # Thank-you page
    path('thank-you/', views.thank_you, name='thank_you'),
]
