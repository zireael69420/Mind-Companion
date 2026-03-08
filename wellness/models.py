# wellness/models.py

from django.db import models
from django.utils import timezone


EMOTION_CHOICES = [
    ('angry',    'Angry'),
    ('anxious',  'Anxious'),
    ('stressed', 'Stressed'),
    ('restless', 'Restless'),
]


class WellnessRating(models.Model):
    """Stores a user's star rating after watching recommended videos."""

    emotion_selected = models.CharField(
        max_length=20,
        choices=EMOTION_CHOICES,
        verbose_name='Emotion Selected',
    )
    rating_score = models.PositiveSmallIntegerField(
        choices=[(i, f'{i} {"star" if i == 1 else "stars"}') for i in range(6)],
        verbose_name='Rating Score (0–5)',
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name='Submitted At',
    )
    # Optional: store which videos were shown (comma-separated YouTube IDs)
    video_ids = models.TextField(
        blank=True,
        verbose_name='Video IDs Shown',
        help_text='Comma-separated YouTube video IDs that were recommended.',
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name='Session Key',
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Wellness Rating'
        verbose_name_plural = 'Wellness Ratings'

    def __str__(self):
        return (
            f'{self.get_emotion_selected_display()} — '
            f'{self.rating_score}★ — '
            f'{self.timestamp.strftime("%Y-%m-%d %H:%M")}'
        )

    def star_display(self):
        return '★' * self.rating_score + '☆' * (5 - self.rating_score)
