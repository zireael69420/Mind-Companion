from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'wellness'

urlpatterns = [
    # Core pages
    path('',                               views.landing,          name='landing'),
    path('recommendations/<str:emotion>/', views.recommendations,  name='recommendations'),
    path('thank-you/',                     views.thank_you,        name='thank_you'),

    # Emotion selection (AJAX POST)
    path('select-emotion/',                views.select_emotion,   name='select_emotion'),

    # Auth
    path('register/',                      views.register_view,    name='register'),
    path('login/',                         views.login_view,       name='login'),
    path('logout/',                        views.logout_view,      name='logout'),

    # 2FA
    path('verify-email/',                  views.verify_email_view, name='verify_email'),
    path('resend-code/',                   views.resend_code_view,  name='resend_code'),

    # Password reset — Django built-in views
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt',
             success_url='/password-reset/done/',
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html',
             success_url='/password-reset-complete/',
         ),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html',
         ),
         name='password_reset_complete'),

    # ── Video-specific feedback (AJAX POST) ──────────────────────────────────
    path('api/video/rate/',     views.video_rate,     name='video_rate'),
    path('api/video/comment/',  views.video_comment,  name='video_comment'),
    path('api/video/feedback/', views.video_feedback, name='video_feedback'),
]
