from django.contrib import admin
from django.utils.html import format_html

from .models import VideoComment, VideoRating


# ── VideoRating ───────────────────────────────────────────────────────────────

@admin.register(VideoRating)
class VideoRatingAdmin(admin.ModelAdmin):
    list_display  = (
        'video_id', 'video_title', 'star_display',
        'user_display', 'created_at', 'updated_at',
    )
    list_filter   = ('score', 'video_id')
    search_fields = ('video_id', 'video_title', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering      = ('-updated_at',)
    date_hierarchy = 'created_at'

    # Show star emojis instead of a bare integer for instant readability
    @admin.display(description='Score', ordering='score')
    def star_display(self, obj):
        return '★' * obj.score + '☆' * (5 - obj.score)

    # Show username or "anonymous" gracefully
    @admin.display(description='User', ordering='user__username')
    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return format_html('<span style="color:#aaa;">anonymous</span>')


# ── VideoComment ──────────────────────────────────────────────────────────────

@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display  = (
        'video_id', 'video_title', 'user_display',
        'body_preview', 'created_at',
    )
    list_filter   = ('video_id',)
    search_fields = ('video_id', 'video_title', 'body', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'

    @admin.display(description='User', ordering='user__username')
    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return format_html('<span style="color:#aaa;">anonymous</span>')

    @admin.display(description='Comment preview')
    def body_preview(self, obj):
        return obj.body[:80] + ('…' if len(obj.body) > 80 else '')
