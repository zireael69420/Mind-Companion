from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class VideoRating(models.Model):
    """
    Per-video star rating (1–5).
    - user is nullable so anonymous users can also rate.
    - unique_together on (user, video_id) prevents logged-in users
      from submitting duplicates; update_or_create is used in the view.
    - Anonymous ratings are allowed but not deduplicated (no session tracking).
    """
    SCORE_CHOICES = [(i, f'{i} star{"s" if i != 1 else ""}') for i in range(1, 6)]

    user        = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='video_ratings',
    )
    video_id    = models.CharField(max_length=20, db_index=True)
    video_title = models.CharField(max_length=255, blank=True)
    score       = models.PositiveSmallIntegerField(choices=SCORE_CHOICES)
    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        # One rating per authenticated user per video
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'video_id'],
                condition=models.Q(user__isnull=False),
                name='unique_user_video_rating',
            )
        ]
        ordering     = ['-updated_at']
        verbose_name = 'Video Rating'

    def __str__(self):
        who = self.user.username if self.user else 'anonymous'
        return f'{who} → {self.video_id} — {self.score}★'


class VideoComment(models.Model):
    """
    Free-text feedback tied to a specific video.
    - user is nullable so anonymous users can comment.
    - video_title is a snapshot stored at write time for admin readability.
    """
    user        = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='video_comments',
    )
    video_id    = models.CharField(max_length=20, db_index=True)
    video_title = models.CharField(max_length=255, blank=True)
    body        = models.TextField(max_length=500)
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering     = ['-created_at']
        verbose_name = 'Video Comment'

    def __str__(self):
        who     = self.user.username if self.user else 'anonymous'
        preview = self.body[:50] + ('…' if len(self.body) > 50 else '')
        return f'{who} on {self.video_id}: "{preview}"'
