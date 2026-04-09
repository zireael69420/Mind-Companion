from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

EMOTION_CHOICES = [
    ('angry',    'Angry'),
    ('anxious',  'Anxious'),
    ('stressed', 'Stressed'),
    ('restless', 'Restless'),
]


class WellnessRating(models.Model):
    """Original session-level rating — kept intact."""
    emotion_selected = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    rating_score     = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(6)]
    )
    timestamp   = models.DateTimeField(default=timezone.now)
    video_ids   = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering     = ['-timestamp']
        verbose_name = 'Wellness Rating (legacy)'

    def __str__(self):
        return f'{self.emotion_selected} — {self.rating_score}★ ({self.timestamp:%Y-%m-%d})'


class VideoRating(models.Model):
    """Per-video star rating tied to a logged-in user.
    unique_together enforces one rating per user per video.
    Re-rating uses update_or_create so it updates instead of duplicating."""
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='video_ratings')
    video_id    = models.CharField(max_length=20)
    video_title = models.CharField(max_length=255, blank=True)
    score       = models.PositiveSmallIntegerField(
        choices=[(i, f'{i} star{"s" if i != 1 else ""}') for i in range(1, 6)]
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'video_id')
        ordering        = ['-updated_at']
        verbose_name    = 'Video Rating'

    def __str__(self):
        return f'{self.user.username} → {self.video_id} — {self.score}★'


class Comment(models.Model):
    """Per-video comment from a logged-in user."""
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    video_id    = models.CharField(max_length=20)
    video_title = models.CharField(max_length=255, blank=True)
    body        = models.TextField(max_length=500)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Video Comment'

    def __str__(self):
        preview = self.body[:40] + ('…' if len(self.body) > 40 else '')
        return f'{self.user.username} on {self.video_id}: "{preview}"'
