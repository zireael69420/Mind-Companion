from django.db import models


EMOTION_CHOICES = [
    ('angry', 'Angry'),
    ('anxious', 'Anxious'),
    ('stressed', 'Stressed'),
    ('restless', 'Restless'),
]


class VideoRecommendation(models.Model):
    """Stores YouTube video metadata for each emotion."""
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    youtube_video_id = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['emotion', 'title']
        verbose_name = 'Video Recommendation'
        verbose_name_plural = 'Video Recommendations'

    def __str__(self):
        return f"[{self.get_emotion_display()}] {self.title}"

    @property
    def embed_url(self):
        return f"https://www.youtube.com/embed/{self.youtube_video_id}"

    @property
    def watch_url(self):
        return f"https://www.youtube.com/watch?v={self.youtube_video_id}"


class WellnessSession(models.Model):
    """Tracks a user session — emotion selected and videos watched."""
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    session_key = models.CharField(max_length=40, blank=True)
    ai_message = models.TextField(blank=True, help_text="AI-generated supportive message for this session")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Wellness Session'
        verbose_name_plural = 'Wellness Sessions'

    def __str__(self):
        return f"Session [{self.get_emotion_display()}] on {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def average_rating(self):
        ratings = self.ratings.all()
        if not ratings:
            return None
        return round(sum(r.stars for r in ratings) / len(ratings), 1)


class VideoRating(models.Model):
    """Star rating (0–5) given by a user after watching a video."""
    STAR_CHOICES = [(i, f'{i} star{"s" if i != 1 else ""}') for i in range(6)]

    session = models.ForeignKey(
        WellnessSession,
        on_delete=models.CASCADE,
        related_name='ratings',
        null=True, blank=True
    )
    video = models.ForeignKey(
        VideoRecommendation,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    stars = models.IntegerField(choices=STAR_CHOICES, default=0)
    feedback = models.TextField(blank=True, help_text="Optional written feedback")
    session_key = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Video Rating'
        verbose_name_plural = 'Video Ratings'

    def __str__(self):
        return f"{self.stars}★ for '{self.video.title}' ({self.get_emotion_display()})"

    def star_display(self):
        return '★' * self.stars + '☆' * (5 - self.stars)
