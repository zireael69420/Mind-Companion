from django.contrib import admin
from django.db import OperationalError, ProgrammingError
from django.utils.html import format_html

from .models import EmailVerification, VideoComment, VideoRating


# ── EmailVerification (2FA) ───────────────────────────────────────────────────

@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display    = ('user', 'code', 'created_at', 'is_used', 'status')
    list_filter     = ('is_used',)
    search_fields   = ('user__username', 'user__email')
    readonly_fields = ('code', 'created_at', 'user')
    ordering        = ('-created_at',)

    def get_queryset(self, request):
        """Fail gracefully if the table doesn't exist yet (pre-migration)."""
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


# ── VideoRating ───────────────────────────────────────────────────────────────

@admin.register(VideoRating)
class VideoRatingAdmin(admin.ModelAdmin):
    list_display    = ('video_id', 'video_title', 'star_display', 'user_display', 'created_at')
    list_filter     = ('score', 'video_id')
    search_fields   = ('video_id', 'video_title', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering        = ('-updated_at',)
    date_hierarchy  = 'created_at'

    @admin.display(description='Score', ordering='score')
    def star_display(self, obj):
        return '★' * obj.score + '☆' * (5 - obj.score)

    @admin.display(description='User', ordering='user__username')
    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return format_html('<span style="color:#aaa;">anonymous</span>')


# ── VideoComment ──────────────────────────────────────────────────────────────

@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display    = ('video_id', 'video_title', 'user_display', 'body_preview', 'created_at')
    list_filter     = ('video_id',)
    search_fields   = ('video_id', 'video_title', 'body', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    ordering        = ('-created_at',)
    date_hierarchy  = 'created_at'

    @admin.display(description='User', ordering='user__username')
    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return format_html('<span style="color:#aaa;">anonymous</span>')

    @admin.display(description='Comment preview')
    def body_preview(self, obj):
        return obj.body[:80] + ('…' if len(obj.body) > 80 else '')
