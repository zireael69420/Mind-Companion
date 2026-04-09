from django.contrib import admin
from django.db import ProgrammingError, OperationalError

from .models import Comment, EmailVerification, VideoRating, WellnessRating


@admin.register(WellnessRating)
class WellnessRatingAdmin(admin.ModelAdmin):
    list_display    = ('emotion_selected', 'rating_score', 'session_key', 'timestamp')
    list_filter     = ('emotion_selected', 'rating_score')
    search_fields   = ('session_key',)
    readonly_fields = ('timestamp',)
    ordering        = ('-timestamp',)


@admin.register(VideoRating)
class VideoRatingAdmin(admin.ModelAdmin):
    list_display    = ('user', 'video_id', 'video_title', 'score', 'updated_at')
    list_filter     = ('score',)
    search_fields   = ('user__username', 'video_id', 'video_title')
    readonly_fields = ('created_at', 'updated_at')
    ordering        = ('-updated_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display    = ('user', 'video_id', 'video_title', 'short_body', 'created_at')
    list_filter     = ('created_at',)
    search_fields   = ('user__username', 'video_id', 'video_title', 'body')
    readonly_fields = ('created_at',)
    ordering        = ('-created_at',)

    @admin.display(description='Comment preview')
    def short_body(self, obj):
        return obj.body[:60] + ('…' if len(obj.body) > 60 else '')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display    = ('user', 'code', 'created_at', 'is_used', 'status')
    list_filter     = ('is_used',)
    search_fields   = ('user__username', 'user__email')
    readonly_fields = ('code', 'created_at', 'user')
    ordering        = ('-created_at',)

    def get_queryset(self, request):
        """Return empty queryset gracefully if the table doesn't exist yet."""
        try:
            return super().get_queryset(request)
        except (ProgrammingError, OperationalError):
            return EmailVerification.objects.none()

    @admin.display(description='Status')
    def status(self, obj):
        if obj.is_used:
            return '✅ Used'
        if obj.is_expired():
            return '⏰ Expired'
        return '🟢 Active'
