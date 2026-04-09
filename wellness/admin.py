from django.contrib import admin

from .models import Comment, VideoRating, WellnessRating


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
