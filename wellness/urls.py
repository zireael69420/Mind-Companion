from django.urls import path

from . import views

app_name = 'wellness'

urlpatterns = [
    # Core pages
    path('',                               views.landing,             name='landing'),
    path('recommendations/<str:emotion>/', views.recommendations,     name='recommendations'),
    path('thank-you/',                     views.thank_you,           name='thank_you'),

    # Emotion selection (AJAX POST)
    path('select-emotion/',                views.select_emotion,      name='select_emotion'),

    # Legacy session-level rating (AJAX POST)
    path('rate/',                          views.submit_rating,       name='submit_rating'),

    # Auth
    path('register/',                      views.register_view,       name='register'),
    path('login/',                         views.login_view,          name='login'),
    path('logout/',                        views.logout_view,         name='logout'),

    # Per-video feedback (AJAX POST)
    path('video-rating/',                  views.submit_video_rating, name='submit_video_rating'),
    path('video-comment/',                 views.submit_comment,      name='submit_comment'),
    path('video-feedback/',                views.get_video_feedback,  name='get_video_feedback'),
]
