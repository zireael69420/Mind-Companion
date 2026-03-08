from django.contrib import admin
from django.utils.html import format_html
from .models import VideoRecommendation, WellnessSession, VideoRating


@admin.register(VideoRecommendation)
class VideoRecommendationAdmin(admin.ModelAdmin):
    list_display = ['title', 'emotion', 'youtube_video_id', 'is_active', 'avg_rating', 'created_at']
    list_filter = ['emotion', 'is_active']
    search_fields = ['title', 'youtube_video_id']
    list_editable = ['is_active']

    def avg_rating(self, obj):
        ratings = obj.ratings.all()
        if not ratings:
            return '—'
        avg = sum(r.stars for r in ratings) / len(ratings)
        return f'{avg:.1f} ★'
    avg_rating.short_description = 'Avg Rating'

    def thumbnail_preview(self, obj):
        if obj.thumbnail_url:
            return format_html('<img src="{}" style="height:60px;border-radius:4px;" />', obj.thumbnail_url)
        return '—'
    thumbnail_preview.short_description = 'Thumbnail'
    readonly_fields = ['thumbnail_preview']


class VideoRatingInline(admin.TabularInline):
    model = VideoRating
    extra = 0
    readonly_fields = ['video', 'stars', 'feedback', 'created_at']


@admin.register(WellnessSession)
class WellnessSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'emotion', 'avg_rating_display', 'created_at']
    list_filter = ['emotion']
    readonly_fields = ['session_key', 'ai_message', 'created_at']
    inlines = [VideoRatingInline]

    def avg_rating_display(self, obj):
        avg = obj.average_rating()
        return f'{avg} ★' if avg is not None else '—'
    avg_rating_display.short_description = 'Avg Rating'


@admin.register(VideoRating)
class VideoRatingAdmin(admin.ModelAdmin):
    list_display = ['star_display_col', 'video', 'emotion', 'feedback_preview', 'created_at']
    list_filter = ['emotion', 'stars']
    search_fields = ['video__title', 'feedback']
    readonly_fields = ['created_at', 'session_key']

    def star_display_col(self, obj):
        return obj.star_display()
    star_display_col.short_description = 'Rating'

    def feedback_preview(self, obj):
        if obj.feedback:
            return obj.feedback[:60] + ('…' if len(obj.feedback) > 60 else '')
        return '—'
    feedback_preview.short_description = 'Feedback'
