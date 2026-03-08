import json
import os
import random
import requests

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import VideoRecommendation, WellnessSession, VideoRating

EMOTION_CONFIG = {
    'angry': {
        'label': 'Angry',
        'emoji': '😤',
        'color': '#FF6B6B',
        'search_query': 'calming anger management meditation',
        'message_hint': 'feeling angry and need to calm down',
        'fallback_videos': [
            {'id': 'MIr3RsUWrdo', 'title': 'Anger Management Meditation'},
            {'id': 'z6X5oEIg6Ak', 'title': 'Calm Your Anger - Breathing Exercise'},
            {'id': 'aXItOY0sLRY', 'title': 'Release Anger - Guided Meditation'},
        ]
    },
    'anxious': {
        'label': 'Anxious',
        'emoji': '😰',
        'color': '#4ECDC4',
        'search_query': 'anxiety relief calming meditation breathing',
        'message_hint': 'feeling anxious and overwhelmed',
        'fallback_videos': [
            {'id': 'O-6f5wQXSu8', 'title': 'Anti-Anxiety Breathing Exercise'},
            {'id': 'yst0hhBEfzA', 'title': 'Anxiety Relief Meditation'},
            {'id': 'ZToicYcHIOU', 'title': '5 Minute Anxiety Meditation'},
        ]
    },
    'stressed': {
        'label': 'Stressed',
        'emoji': '😩',
        'color': '#A8E6CF',
        'search_query': 'stress relief relaxation meditation music',
        'message_hint': 'feeling very stressed and burned out',
        'fallback_videos': [
            {'id': '4EaMJOo1jks', 'title': 'Stress Relief Meditation'},
            {'id': 'mMHkLR5JCAI', 'title': 'Relaxing Music for Stress'},
            {'id': 'ODfWtnECwdU', 'title': '10 Minute Stress Relief'},
        ]
    },
    'restless': {
        'label': 'Restless',
        'emoji': '😶',
        'color': '#FFD93D',
        'search_query': 'sleep relaxation calm restless mind meditation',
        'message_hint': 'feeling restless and unable to settle',
        'fallback_videos': [
            {'id': 'inpok4MKVLM', 'title': 'Calm Restless Mind Meditation'},
            {'id': '1ZYbU82uLEk', 'title': 'Deep Sleep Relaxation'},
            {'id': 'lFcSrYw2VjY', 'title': 'Peaceful Music for Restlessness'},
        ]
    },
}


def get_ai_message(emotion):
    """Generate a compassionate AI message using Anthropic API."""
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        return _default_message(emotion)

    config = EMOTION_CONFIG.get(emotion, {})
    hint = config.get('message_hint', f'feeling {emotion}')

    try:
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 150,
                'messages': [{
                    'role': 'user',
                    'content': (
                        f'You are Mellow, a gentle wellness mascot. '
                        f'A user is {hint}. '
                        f'Write a single warm, empathetic 2-sentence message to comfort them '
                        f'and encourage them to watch some helpful videos. '
                        f'Keep it gentle, non-clinical, and friendly.'
                    )
                }]
            },
            timeout=10
        )
        data = response.json()
        return data['content'][0]['text'].strip()
    except Exception:
        return _default_message(emotion)


def _default_message(emotion):
    defaults = {
        'angry': "It's okay to feel angry — your feelings are valid. Let's find something to help you breathe and release that tension. 💙",
        'anxious': "Anxiety can feel so overwhelming, but you're not alone. I've picked some gentle videos to help you find your calm. 🌿",
        'stressed': "You've been carrying so much — let's take a moment together. These videos are here to help you decompress and breathe. ☁️",
        'restless': "That restless feeling is hard to sit with. Let's guide your mind somewhere peaceful with these soothing videos. 🌙",
    }
    return defaults.get(emotion, "I'm here for you. Let's find something calming together. 💫")


def fetch_youtube_videos(emotion):
    """Fetch videos from YouTube API or fall back to DB then hardcoded."""
    # 1. Try DB first
    db_videos = VideoRecommendation.objects.filter(emotion=emotion, is_active=True)
    if db_videos.exists():
        videos = list(db_videos.values('youtube_video_id', 'title', 'thumbnail_url', 'id'))
        for v in videos:
            v['embed_url'] = f"https://www.youtube.com/embed/{v['youtube_video_id']}"
        return videos

    # 2. Try YouTube Data API
    api_key = settings.YOUTUBE_API_KEY
    if api_key:
        config = EMOTION_CONFIG.get(emotion, {})
        query = config.get('search_query', emotion)
        try:
            resp = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'part': 'snippet',
                    'q': query,
                    'type': 'video',
                    'videoCategoryId': '26',
                    'maxResults': 4,
                    'key': api_key,
                    'relevanceLanguage': 'en',
                    'safeSearch': 'strict',
                },
                timeout=8
            )
            data = resp.json()
            videos = []
            for item in data.get('items', []):
                vid_id = item['id']['videoId']
                snippet = item['snippet']
                videos.append({
                    'youtube_video_id': vid_id,
                    'title': snippet['title'],
                    'thumbnail_url': snippet['thumbnails']['medium']['url'],
                    'embed_url': f"https://www.youtube.com/embed/{vid_id}",
                    'id': None,
                })
            if videos:
                return videos
        except Exception:
            pass

    # 3. Hardcoded fallback
    config = EMOTION_CONFIG.get(emotion, {})
    fallbacks = config.get('fallback_videos', [])
    return [
        {
            'youtube_video_id': v['id'],
            'title': v['title'],
            'thumbnail_url': f"https://img.youtube.com/vi/{v['id']}/mqdefault.jpg",
            'embed_url': f"https://www.youtube.com/embed/{v['id']}",
            'id': None,
        }
        for v in fallbacks
    ]


# ── Views ──────────────────────────────────────────────────────────────────────

def landing(request):
    """Landing page — mascot asks how you're feeling."""
    return render(request, 'wellness/landing.html', {
        'emotions': EMOTION_CONFIG,
    })


def recommendations(request, emotion):
    """Show video recommendations for the chosen emotion."""
    if emotion not in EMOTION_CONFIG:
        from django.http import Http404
        raise Http404("Emotion not found")

    config = EMOTION_CONFIG[emotion]
    videos = fetch_youtube_videos(emotion)
    ai_message = get_ai_message(emotion)

    # Create session
    session_key = request.session.session_key or ''
    if not request.session.session_key:
        request.session.create()
        session_key = request.session.session_key

    session = WellnessSession.objects.create(
        emotion=emotion,
        session_key=session_key,
        ai_message=ai_message,
    )

    return render(request, 'wellness/recommendations.html', {
        'emotion': emotion,
        'config': config,
        'videos': videos,
        'ai_message': ai_message,
        'session_id': session.id,
        'emotions': EMOTION_CONFIG,
    })


@require_POST
def submit_rating(request):
    """Ajax endpoint — save a star rating for a video."""
    try:
        data = json.loads(request.body)
        stars = int(data.get('stars', 0))
        emotion = data.get('emotion', '')
        video_id_str = data.get('video_id')
        session_id = data.get('session_id')
        feedback = data.get('feedback', '')

        if emotion not in EMOTION_CONFIG or stars < 0 or stars > 5:
            return JsonResponse({'error': 'Invalid data'}, status=400)

        session = None
        if session_id:
            try:
                session = WellnessSession.objects.get(id=session_id)
            except WellnessSession.DoesNotExist:
                pass

        video = None
        if video_id_str:
            try:
                video = VideoRecommendation.objects.get(id=int(video_id_str))
            except (VideoRecommendation.DoesNotExist, ValueError):
                # Create a minimal record
                yt_id = data.get('youtube_video_id', '')
                title = data.get('title', 'Unknown Video')
                if yt_id:
                    video, _ = VideoRecommendation.objects.get_or_create(
                        youtube_video_id=yt_id,
                        emotion=emotion,
                        defaults={'title': title}
                    )

        if video is None:
            return JsonResponse({'error': 'Video not found'}, status=400)

        session_key = request.session.session_key or ''
        rating = VideoRating.objects.create(
            session=session,
            video=video,
            emotion=emotion,
            stars=stars,
            feedback=feedback,
            session_key=session_key,
        )

        return JsonResponse({'success': True, 'rating_id': rating.id})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def thank_you(request):
    """Thank-you page after rating."""
    emotion = request.GET.get('emotion', '')
    config = EMOTION_CONFIG.get(emotion, {})
    return render(request, 'wellness/thank_you.html', {
        'emotion': emotion,
        'config': config,
        'emotions': EMOTION_CONFIG,
    })
