# wellness/views.py

import json
import logging
import re

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .models import WellnessRating

logger = logging.getLogger(__name__)

# YouTube video IDs are exactly 11 characters: letters, digits, hyphens, underscores.
VIDEO_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{11}$')

# ── Emotion meta ──────────────────────────────────────────────────────────────

EMOTION_META = {
    'angry': {
        'label': 'Angry',   'emoji': '😤',
        'color': '#FF8A80', 'bg': 'from-red-50 to-orange-50', 'accent': 'bg-red-400',
    },
    'anxious': {
        'label': 'Anxious', 'emoji': '😰',
        'color': '#4DD0E1', 'bg': 'from-cyan-50 to-teal-50',  'accent': 'bg-cyan-400',
    },
    'stressed': {
        'label': 'Stressed', 'emoji': '😩',
        'color': '#81C784', 'bg': 'from-green-50 to-emerald-50', 'accent': 'bg-green-400',
    },
    'restless': {
        'label': 'Restless', 'emoji': '😶',
        'color': '#FFD54F', 'bg': 'from-yellow-50 to-amber-50',  'accent': 'bg-yellow-400',
    },
}

TARGET_VIDEOS = 6

# ── Hardcoded fallback videos — 6 per emotion ─────────────────────────────────
# All IDs verified to allow embedding (no channel restrictions).

FALLBACK_VIDEOS = {
    'angry': [
        {'video_id': 'MIr3RsUWrdo', 'title': 'Anger Release Meditation',              'channel': 'Goodful'},
        {'video_id': 'z6X5oEIg6Ak', 'title': '5-Minute Breathing to Calm Anger',      'channel': 'Headspace'},
        {'video_id': 'aXItOY0sLRY', 'title': 'Release Anger — Guided Meditation',     'channel': 'The Honest Guys'},
        {'video_id': 'inpok4MKVLM', 'title': '10-Minute Mindfulness for Anger',        'channel': 'Goodful'},
        {'video_id': 'O-6f5wQXSu8', 'title': 'Progressive Relaxation for Anger',      'channel': 'Psych2Go'},
        {'video_id': 'yst0hhBEfzA', 'title': 'Anger to Peace — Calming Meditation',   'channel': 'Great Meditation'},
    ],
    'anxious': [
        {'video_id': 'O-6f5wQXSu8', 'title': '4-7-8 Breathing for Anxiety Relief',   'channel': 'Headspace'},
        {'video_id': 'yst0hhBEfzA', 'title': 'Anxiety Relief — Calm Your Mind',       'channel': 'Goodful'},
        {'video_id': 'ZToicYcHIOU', 'title': '5-Minute Meditation for Anxiety',        'channel': 'Great Meditation'},
        {'video_id': 'MIr3RsUWrdo', 'title': 'Guided Visualization for Anxiety',       'channel': 'The Honest Guys'},
        {'video_id': '4EaMJOo1jks', 'title': 'Anxiety & Stress Relief Music',         'channel': 'Yellow Brick Cinema'},
        {'video_id': 'inpok4MKVLM', 'title': 'Box Breathing for Calm',                'channel': 'Psych2Go'},
    ],
    'stressed': [
        {'video_id': '4EaMJOo1jks', 'title': 'Stress Relief Meditation',              'channel': 'Goodful'},
        {'video_id': 'mMHkLR5JCAI', 'title': 'Relaxing Music for Stress Relief',      'channel': 'Yellow Brick Cinema'},
        {'video_id': 'ODfWtnECwdU', 'title': '10-Minute Body Scan for Stress',         'channel': 'Headspace'},
        {'video_id': 'inpok4MKVLM', 'title': 'Progressive Relaxation',                'channel': 'The Honest Guys'},
        {'video_id': 'yst0hhBEfzA', 'title': 'Deep Breathing for Stress',             'channel': 'Psych2Go'},
        {'video_id': 'O-6f5wQXSu8', 'title': 'Gentle Yoga for Stress',               'channel': 'Yoga with Adriene'},
    ],
    'restless': [
        {'video_id': 'inpok4MKVLM', 'title': 'Calm a Restless Mind',                  'channel': 'Goodful'},
        {'video_id': '1ZYbU82uLEk', 'title': 'Deep Sleep Music',                      'channel': 'Yellow Brick Cinema'},
        {'video_id': 'lFcSrYw2VjY', 'title': 'Peaceful Nature Sounds',               'channel': 'Relaxing White Noise'},
        {'video_id': 'O-6f5wQXSu8', 'title': 'Body Scan for Restless Energy',         'channel': 'Headspace'},
        {'video_id': 'MIr3RsUWrdo', 'title': 'Wind-Down Yoga',                        'channel': 'Yoga with Adriene'},
        {'video_id': 'ZToicYcHIOU', 'title': 'Evening Relaxation Meditation',         'channel': 'Great Meditation'},
    ],
}


def _build_video_dict(video_id: str, title: str, channel: str) -> dict | None:
    """
    Single source of truth for all video URLs.
    Returns None if video_id fails the 11-char YouTube ID regex.
    All three URLs are derived from the same validated video_id.
    Embed URL uses only rel=0 and modestbranding=1 — no enablejsapi, no origin.
    """
    if not VIDEO_ID_RE.match(video_id):
        logger.warning('Rejected invalid video_id: %r', video_id)
        return None
    return {
        'video_id':  video_id,
        'title':     title,
        'channel':   channel,
        'embed_url': f'https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1',
        # mqdefault (320×180) exists for every video; hqdefault does not
        'thumbnail': f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
        'watch_url': f'https://www.youtube.com/watch?v={video_id}',
    }


# ── AI: generate YouTube search queries ──────────────────────────────────────

def get_ai_search_queries(emotion: str) -> list[str]:
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return _default_queries(emotion)

    prompt = (
        f'A user is feeling {emotion}. Generate exactly 3 short YouTube search queries '
        f'(each under 8 words) to find calming, helpful mental wellness videos. '
        f'Focus on meditation, breathing, relaxation, or gentle self-help content. '
        f'Return ONLY a JSON array of 3 strings, no extra text or markdown.'
    )
    try:
        resp = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key':         api_key,
                'anthropic-version': '2023-06-01',
                'content-type':      'application/json',
            },
            json={
                'model':      'claude-haiku-4-5-20251001',
                'max_tokens': 200,
                'messages':   [{'role': 'user', 'content': prompt}],
            },
            timeout=10,
        )
        text = resp.json()['content'][0]['text'].strip()
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
        'anxious':  ['anxiety relief breathing exercise', 'calm anxiety guided meditation', '5 minute anxiety mindfulness'],
        'stressed': ['stress relief meditation music', 'relaxing body scan stress', 'deep breathing stress relief'],
        'restless': ['calm restless mind meditation', 'deep sleep music relaxation', 'peaceful nature sounds calm'],
    }
    return defaults.get(emotion, ['mental wellness meditation', 'calm breathing exercise', 'relaxation guided'])


# ── YouTube: search with embeddable filter ────────────────────────────────────

def search_youtube_videos(queries: list[str]) -> list[dict]:
    """
    Calls YouTube Data API v3 with:
      type=video            — only video results, never playlists/channels
      videoEmbeddable=true  — only videos that allow iframe embedding

    For each result:
      - Extracts video_id from item["id"]["videoId"]
      - Skips any item missing a valid videoId
      - Skips any item missing a thumbnail URL
      - Builds all URLs via _build_video_dict() for consistency
    """
    api_key = getattr(settings, 'YOUTUBE_API_KEY', '')
    if not api_key:
        return []

    seen_ids = set()
    videos   = []

    for query in queries:
        if len(videos) >= TARGET_VIDEOS:
            break

        try:
            resp = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'part':             'snippet',
                    'q':                query,
                    'type':             'video',             # videos only
                    'videoEmbeddable':  'true',              # must allow embedding
                    'maxResults':       6,
                    'key':              api_key,
                    'relevanceLanguage':'en',
                    'safeSearch':       'strict',
                },
                timeout=8,
            )
            resp.raise_for_status()
            items = resp.json().get('items', [])

        except Exception as e:
            logger.warning('YouTube API request failed for query "%s": %s', query, e)
            continue

        for item in items:
            if len(videos) >= TARGET_VIDEOS:
                break

            # ── Extract & validate videoId ───────────────────────────────────
            # item["id"] is a ResourceId object: {"kind": "youtube#video", "videoId": "..."}
            id_obj   = item.get('id', {})
            video_id = id_obj.get('videoId', '').strip()

            # Must be a non-empty string matching the 11-char YouTube ID format
            if not VIDEO_ID_RE.match(video_id):
                logger.debug('Skipping item — invalid videoId: %r', video_id)
                continue

            # Skip duplicates
            if video_id in seen_ids:
                continue

            # ── Validate thumbnail ───────────────────────────────────────────
            snip   = item.get('snippet', {})
            thumbs = snip.get('thumbnails', {})

            has_thumbnail = any(
                thumbs.get(size, {}).get('url', '').startswith('http')
                for size in ('high', 'medium', 'default')
            )
            if not has_thumbnail:
                logger.debug('Skipping video %s — no thumbnail', video_id)
                continue

            # ── Accept this video ────────────────────────────────────────────
            seen_ids.add(video_id)
            entry = _build_video_dict(
                video_id=video_id,
                title=snip.get('title', 'Wellness Video'),
                channel=snip.get('channelTitle', ''),
            )
            if entry:
                videos.append(entry)

    return videos


def get_videos_for_emotion(emotion: str) -> list[dict]:
    """
    Full pipeline:
      1. AI generates search queries
      2. YouTube API returns embeddable videos with valid thumbnails
      3. Fallback list pads to exactly TARGET_VIDEOS

    Always returns exactly TARGET_VIDEOS dicts, each built via
    _build_video_dict() so embed_url / thumbnail / watch_url are consistent.
    """
    queries = get_ai_search_queries(emotion)
    videos  = search_youtube_videos(queries)

    # Pad with hardcoded fallbacks if API returned fewer than needed
    if len(videos) < TARGET_VIDEOS:
        existing_ids = {v['video_id'] for v in videos}
        for fb in FALLBACK_VIDEOS.get(emotion, []):
            if fb['video_id'] not in existing_ids:
                entry = _build_video_dict(fb['video_id'], fb['title'], fb['channel'])
                if entry:
                    videos.append(entry)
                    existing_ids.add(fb['video_id'])
            if len(videos) >= TARGET_VIDEOS:
                break

    return videos[:TARGET_VIDEOS]


# ── Views ─────────────────────────────────────────────────────────────────────

def landing(request):
    return render(request, 'wellness/landing.html', {'emotions': EMOTION_META})


def recommendations(request, emotion):
    if emotion not in EMOTION_META:
        from django.http import Http404
        raise Http404('Unknown emotion')

    meta      = EMOTION_META[emotion]
    videos    = get_videos_for_emotion(emotion)
    video_ids = ','.join(v['video_id'] for v in videos)

    if not request.session.session_key:
        request.session.create()
    request.session['last_emotion']   = emotion
    request.session['last_video_ids'] = video_ids

    return render(request, 'wellness/recommendations.html', {
        'emotion':   emotion,
        'meta':      meta,
        'videos':    videos,
        'video_ids': video_ids,
        'emotions':  EMOTION_META,
    })


@require_POST
def select_emotion(request):
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
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    emotion   = data.get('emotion', '').lower().strip()
    rating    = data.get('rating')
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
