# wellness/admin.py

from django.contrib import admin
from .models import WellnessRating


@admin.register(WellnessRating)
class WellnessRatingAdmin(admin.ModelAdmin):
    list_display  = ['emotion_selected', 'star_display', 'timestamp', 'session_key']
    list_filter   = ['emotion_selected', 'rating_score']
    search_fields = ['emotion_selected', 'session_key']
    readonly_fields = ['timestamp', 'session_key', 'video_ids']
    ordering = ['-timestamp']

    def star_display(self, obj):
        return obj.star_display()
    star_display.short_description = 'Rating'
