# wellness/views.py

import json
import logging
import os

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import WellnessRating

logger = logging.getLogger(__name__)

# ── Emotion meta ──────────────────────────────────────────────────────────────

EMOTION_META = {
    'angry': {
        'label':  'Angry',
        'emoji':  '😤',
        'color':  '#FF8A80',
        'bg':     'from-red-50 to-orange-50',
        'accent': 'bg-red-400',
    },
    'anxious': {
        'label':  'Anxious',
        'emoji':  '😰',
        'color':  '#4DD0E1',
        'bg':     'from-cyan-50 to-teal-50',
        'accent': 'bg-cyan-400',
    },
    'stressed': {
        'label':  'Stressed',
        'emoji':  '😩',
        'color':  '#81C784',
        'bg':     'from-green-50 to-emerald-50',
        'accent': 'bg-green-400',
    },
    'restless': {
        'label':  'Restless',
        'emoji':  '😶',
        'color':  '#FFD54F',
        'bg':     'from-yellow-50 to-amber-50',
        'accent': 'bg-yellow-400',
    },
}

# ── Hardcoded fallback videos (used when APIs are unavailable) ─────────────────

FALLBACK_VIDEOS = {
    'angry': [
        {'id': 'MIr3RsUWrdo', 'title': 'Anger Release Meditation — Let Go of Anger', 'channel': 'Goodful'},
        {'id': 'z6X5oEIg6Ak', 'title': '5-Minute Breathing Exercise to Calm Anger',  'channel': 'Headspace'},
        {'id': 'aXItOY0sLRY', 'title': 'Release Anger Guided Meditation',             'channel': 'The Honest Guys'},
        {'id': 'inpok4MKVLM', 'title': '10-Minute Mindfulness for Anger',             'channel': 'Goodful'},
        {'id': 'O-6f5wQXSu8', 'title': 'Progressive Muscle Relaxation for Anger',     'channel': 'Psych2Go'},
    ],
    'anxious': [
        {'id': 'O-6f5wQXSu8', 'title': '4-7-8 Breathing for Anxiety Relief',          'channel': 'Headspace'},
        {'id': 'yst0hhBEfzA', 'title': 'Anxiety Relief — Calm Your Mind Meditation',  'channel': 'Goodful'},
        {'id': 'ZToicYcHIOU', 'title': '5-Minute Meditation for Anxiety',              'channel': 'Great Meditation'},
        {'id': 'MIr3RsUWrdo', 'title': 'Guided Visualization for Anxiety',             'channel': 'The Honest Guys'},
        {'id': '4EaMJOo1jks', 'title': 'Anxiety & Stress Relief Music',                'channel': 'Yellow Brick Cinema'},
    ],
    'stressed': [
        {'id': '4EaMJOo1jks', 'title': 'Stress Relief Meditation — Calm Your Mind',   'channel': 'Goodful'},
        {'id': 'mMHkLR5JCAI', 'title': 'Relaxing Music for Stress Relief',             'channel': 'Yellow Brick Cinema'},
        {'id': 'ODfWtnECwdU', 'title': '10-Minute Body Scan for Stress',               'channel': 'Headspace'},
        {'id': 'inpok4MKVLM', 'title': 'Progressive Relaxation — Full Body Release',  'channel': 'The Honest Guys'},
        {'id': 'yst0hhBEfzA', 'title': 'Deep Breathing Exercises to Reduce Stress',   'channel': 'Psych2Go'},
    ],
    'restless': [
        {'id': 'inpok4MKVLM', 'title': 'Calm a Restless Mind — Guided Meditation',    'channel': 'Goodful'},
        {'id': '1ZYbU82uLEk', 'title': 'Deep Sleep Music — Quiet a Restless Mind',    'channel': 'Yellow Brick Cinema'},
        {'id': 'lFcSrYw2VjY', 'title': 'Peaceful Nature Sounds for Restlessness',     'channel': 'Relaxing White Noise'},
        {'id': 'O-6f5wQXSu8', 'title': 'Body Scan Meditation for Restless Energy',    'channel': 'Headspace'},
        {'id': 'MIr3RsUWrdo', 'title': 'Wind-Down Yoga for Restless Feelings',        'channel': 'Yoga with Adriene'},
    ],
}


# ── AI: generate YouTube search queries via Claude ────────────────────────────

def get_ai_search_queries(emotion: str) -> list[str]:
    """
    Ask Claude to generate 3 YouTube search queries for the given emotion.
    Returns a list of query strings, or falls back to defaults.
    """
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return _default_queries(emotion)

    prompt = (
        f'A user is feeling {emotion}. Generate exactly 3 short YouTube search queries '
        f'(each under 8 words) to find calming, helpful mental wellness videos for someone '
        f'experiencing this emotion. Focus on meditation, breathing, relaxation, or gentle '
        f'self-help content. Return ONLY a JSON array of 3 strings, nothing else. '
        f'Example: ["calm anxiety breathing exercise", "guided meditation for worry", '
        f'"5 minute mindfulness anxiety relief"]'
    )

    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
            },
            json={
                'model': 'claude-haiku-4-5-20251001',
                'max_tokens': 200,
                'messages': [{'role': 'user', 'content': prompt}],
            },
            timeout=10,
        )
        text = resp.json()['content'][0]['text'].strip()
        # Strip markdown code fences if present
        text = text.replace('```json', '').replace('```', '').strip()
        queries = json.loads(text)
        if isinstance(queries, list) and len(queries) >= 1:
            return queries[:3]
    except Exception as e:
        logger.warning('Claude API error: %s', e)

    return _default_queries(emotion)


def _default_queries(emotion: str) -> list[str]:
    defaults = {
        'angry':    ['release anger meditation', 'calm anger breathing exercise', 'anger management guided meditation'],
        'anxious':  ['anxiety relief breathing', 'calm anxiety guided meditation', '5 minute anxiety relief'],
        'stressed': ['stress relief meditation', 'relaxing music stress', 'body scan stress release'],
        'restless': ['calm restless mind meditation', 'deep sleep music restless', 'peaceful nature sounds relaxation'],
    }
    return defaults.get(emotion, ['mental wellness meditation', 'calm mind breathing', 'relaxation guide'])


# ── YouTube: search videos ────────────────────────────────────────────────────

def search_youtube_videos(queries: list[str], max_per_query: int = 2) -> list[dict]:
    """
    Search YouTube Data API v3 for each query and return up to 5 unique videos.
    Falls back to an empty list on failure.
    """
    api_key = getattr(settings, 'YOUTUBE_API_KEY', '')
    if not api_key:
        return []

    seen_ids = set()
    videos   = []

    for query in queries:
        if len(videos) >= 5:
            break
        try:
            resp = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'part':             'snippet',
                    'q':                query,
                    'type':             'video',
                    'maxResults':       max_per_query,
                    'key':              api_key,
                    'relevanceLanguage':'en',
                    'safeSearch':       'strict',
                    'videoCategoryId':  '26',  # Howto & Style (wellness-adjacent)
                },
                timeout=8,
            )
            for item in resp.json().get('items', []):
                vid_id = item['id']['videoId']
                if vid_id in seen_ids:
                    continue
                seen_ids.add(vid_id)
                snip = item['snippet']
                videos.append({
                    'id':        vid_id,
                    'title':     snip['title'],
                    'channel':   snip['channelTitle'],
                    'thumbnail': snip['thumbnails']['medium']['url'],
                })
                if len(videos) >= 5:
                    break
        except Exception as e:
            logger.warning('YouTube API error for query "%s": %s', query, e)

    return videos


def get_videos_for_emotion(emotion: str) -> list[dict]:
    """
    Full pipeline: AI queries → YouTube search → fallback.
    Always returns exactly 5 video dicts with keys: id, title, channel, thumbnail.
    """
    queries = get_ai_search_queries(emotion)
    videos  = search_youtube_videos(queries)

    if len(videos) < 5:
        # Pad with fallbacks (avoid duplicates)
        existing_ids = {v['id'] for v in videos}
        for fb in FALLBACK_VIDEOS.get(emotion, []):
            if fb['id'] not in existing_ids:
                videos.append({
                    'id':        fb['id'],
                    'title':     fb['title'],
                    'channel':   fb['channel'],
                    'thumbnail': f"https://img.youtube.com/vi/{fb['id']}/mqdefault.jpg",
                })
                existing_ids.add(fb['id'])
            if len(videos) >= 5:
                break

    return videos[:5]


# ── Views ─────────────────────────────────────────────────────────────────────

def landing(request):
    """Landing page — mascot + emotion selector."""
    return render(request, 'wellness/landing.html', {
        'emotions': EMOTION_META,
    })


def recommendations(request, emotion):
    """
    Recommendation page.
    Accepts both GET (direct URL) and POST (AJAX redirect target).
    """
    if emotion not in EMOTION_META:
        from django.http import Http404
        raise Http404('Unknown emotion')

    meta   = EMOTION_META[emotion]
    videos = get_videos_for_emotion(emotion)

    # Store video IDs in session for the rating step
    video_ids = ','.join(v['id'] for v in videos)
    if not request.session.session_key:
        request.session.create()
    request.session['last_emotion']  = emotion
    request.session['last_video_ids'] = video_ids

    return render(request, 'wellness/recommendations.html', {
        'emotion':    emotion,
        'meta':       meta,
        'videos':     videos,
        'video_ids':  video_ids,
        'emotions':   EMOTION_META,
    })


@require_POST
def select_emotion(request):
    """
    AJAX endpoint: receives { emotion } JSON, returns { redirect_url }.
    Used by the landing page fetch() call.
    """
    try:
        data    = json.loads(request.body)
        emotion = data.get('emotion', '').lower().strip()
    except (json.JSONDecodeError, AttributeError):
        emotion = ''

    if emotion not in EMOTION_META:
        return JsonResponse({'error': 'Invalid emotion'}, status=400)

    from django.urls import reverse
    return JsonResponse({'redirect_url': reverse('wellness:recommendations', args=[emotion])})


@require_POST
def submit_rating(request):
    """AJAX endpoint: receives { emotion, rating, video_ids } and saves to DB."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    emotion  = data.get('emotion', '').lower().strip()
    rating   = data.get('rating')
    video_ids = data.get('video_ids', '')

    if emotion not in EMOTION_META:
        return JsonResponse({'error': 'Invalid emotion'}, status=400)

    try:
        rating = int(rating)
        assert 0 <= rating <= 5
    except (TypeError, ValueError, AssertionError):
        return JsonResponse({'error': 'Rating must be 0–5'}, status=400)

    if not request.session.session_key:
        request.session.create()

    WellnessRating.objects.create(
        emotion_selected=emotion,
        rating_score=rating,
        video_ids=video_ids,
        session_key=request.session.session_key,
    )

    from django.urls import reverse
    return JsonResponse({
        'success':      True,
        'redirect_url': reverse('wellness:thank_you') + f'?emotion={emotion}&stars={rating}',
    })


def thank_you(request):
    """Thank-you page shown after rating is submitted."""
    emotion = request.GET.get('emotion', '')
    stars   = request.GET.get('stars', '0')
    meta    = EMOTION_META.get(emotion, {})

    try:
        stars = int(stars)
    except ValueError:
        stars = 0

    return render(request, 'wellness/thank_you.html', {
        'emotion':  emotion,
        'meta':     meta,
        'stars':    stars,
        'emotions': EMOTION_META,
    })
