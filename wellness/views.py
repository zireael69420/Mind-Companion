import html
import json
import logging
import random
import re
import string

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import RegisterForm, VerifyCodeForm
from .models import EmailVerification, VideoComment, VideoRating, WatchHistory

logger = logging.getLogger(__name__)

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

FALLBACK_VIDEOS = {
    'angry': [
        {'video_id': 'MIr3RsUWrdo', 'title': 'Anger Release Meditation',            'channel': 'Goodful'},
        {'video_id': 'z6X5oEIg6Ak', 'title': '5-Minute Breathing to Calm Anger',    'channel': 'Headspace'},
        {'video_id': 'aXItOY0sLRY', 'title': 'Release Anger — Guided Meditation',   'channel': 'The Honest Guys'},
        {'video_id': 'inpok4MKVLM', 'title': '10-Minute Mindfulness for Anger',     'channel': 'Goodful'},
        {'video_id': 'O-6f5wQXSu8', 'title': 'Progressive Relaxation for Anger',   'channel': 'Psych2Go'},
        {'video_id': 'yst0hhBEfzA', 'title': 'Anger to Peace — Calming Meditation', 'channel': 'Great Meditation'},
    ],
    'anxious': [
        {'video_id': 'O-6f5wQXSu8', 'title': '4-7-8 Breathing for Anxiety Relief', 'channel': 'Headspace'},
        {'video_id': 'yst0hhBEfzA', 'title': 'Anxiety Relief — Calm Your Mind',     'channel': 'Goodful'},
        {'video_id': 'ZToicYcHIOU', 'title': '5-Minute Meditation for Anxiety',     'channel': 'Great Meditation'},
        {'video_id': 'MIr3RsUWrdo', 'title': 'Guided Visualization for Anxiety',    'channel': 'The Honest Guys'},
        {'video_id': '4EaMJOo1jks', 'title': 'Anxiety & Stress Relief Music',       'channel': 'Yellow Brick Cinema'},
        {'video_id': 'inpok4MKVLM', 'title': 'Box Breathing for Calm',              'channel': 'Psych2Go'},
    ],
    'stressed': [
        {'video_id': '4EaMJOo1jks', 'title': 'Stress Relief Meditation',            'channel': 'Goodful'},
        {'video_id': 'mMHkLR5JCAI', 'title': 'Relaxing Music for Stress Relief',    'channel': 'Yellow Brick Cinema'},
        {'video_id': 'ODfWtnECwdU', 'title': '10-Minute Body Scan for Stress',      'channel': 'Headspace'},
        {'video_id': 'inpok4MKVLM', 'title': 'Progressive Relaxation',              'channel': 'The Honest Guys'},
        {'video_id': 'yst0hhBEfzA', 'title': 'Deep Breathing for Stress',           'channel': 'Psych2Go'},
        {'video_id': 'O-6f5wQXSu8', 'title': 'Gentle Yoga for Stress',             'channel': 'Yoga with Adriene'},
    ],
    'restless': [
        {'video_id': 'inpok4MKVLM', 'title': 'Calm a Restless Mind',                'channel': 'Goodful'},
        {'video_id': '1ZYbU82uLEk', 'title': 'Deep Sleep Music',                    'channel': 'Yellow Brick Cinema'},
        {'video_id': 'lFcSrYw2VjY', 'title': 'Peaceful Nature Sounds',             'channel': 'Relaxing White Noise'},
        {'video_id': 'O-6f5wQXSu8', 'title': 'Body Scan for Restless Energy',      'channel': 'Headspace'},
        {'video_id': 'MIr3RsUWrdo', 'title': 'Wind-Down Yoga',                      'channel': 'Yoga with Adriene'},
        {'video_id': 'ZToicYcHIOU', 'title': 'Evening Relaxation Meditation',       'channel': 'Great Meditation'},
    ],
}


def _build_video_dict(video_id, title, channel):
    if not VIDEO_ID_RE.match(video_id):
        logger.warning('Rejected invalid video_id: %r', video_id)
        return None
    return {
        'video_id':  video_id,
        'title':     title,
        'channel':   channel,
        'embed_url': f'https://www.youtube.com/embed/{video_id}?rel=0&modestbranding=1',
        'thumbnail': f'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
        'watch_url': f'https://www.youtube.com/watch?v={video_id}',
    }


# ── AI + YouTube ──────────────────────────────────────────────────────────────

def get_ai_search_queries(emotion):
    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
    if not api_key:
        return _default_queries(emotion)
    prompt = (
        f'A user is feeling {emotion}. Generate exactly 3 short YouTube search queries '
        f'(each under 8 words) to find calming, helpful mental wellness videos. '
        f'Focus on meditation, breathing, relaxation. '
        f'Return ONLY a JSON array of 3 strings, no extra text or markdown.'
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
        text = text.replace('```json', '').replace('```', '').strip()
        queries = json.loads(text)
        if isinstance(queries, list) and queries:
            return queries[:3]
    except Exception as e:
        logger.warning('Claude API error: %s', e)
    return _default_queries(emotion)


def _default_queries(emotion):
    return {
        'angry':    ['release anger meditation', 'calm anger breathing exercise', 'anger management guided meditation'],
        'anxious':  ['anxiety relief breathing exercise', 'calm anxiety guided meditation', '5 minute anxiety mindfulness'],
        'stressed': ['stress relief meditation music', 'relaxing body scan stress', 'deep breathing stress relief'],
        'restless': ['calm restless mind meditation', 'deep sleep music relaxation', 'peaceful nature sounds calm'],
    }.get(emotion, ['mental wellness meditation', 'calm breathing exercise', 'relaxation guided'])


def search_youtube_videos(queries):
    api_key = getattr(settings, 'YOUTUBE_API_KEY', '')
    if not api_key:
        return []
    seen_ids, videos = set(), []
    for query in queries:
        if len(videos) >= TARGET_VIDEOS:
            break
        try:
            resp = requests.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'part': 'snippet', 'q': query, 'type': 'video',
                    'videoEmbeddable': 'true', 'maxResults': 6,
                    'key': api_key, 'relevanceLanguage': 'en', 'safeSearch': 'strict',
                },
                timeout=8,
            )
            resp.raise_for_status()
            for item in resp.json().get('items', []):
                if len(videos) >= TARGET_VIDEOS:
                    break
                video_id = item.get('id', {}).get('videoId', '').strip()
                if not VIDEO_ID_RE.match(video_id) or video_id in seen_ids:
                    continue
                snip   = item.get('snippet', {})
                thumbs = snip.get('thumbnails', {})
                if not any(thumbs.get(s, {}).get('url', '').startswith('http')
                           for s in ('high', 'medium', 'default')):
                    continue
                seen_ids.add(video_id)
                entry = _build_video_dict(
                    video_id=video_id,
                    title=html.unescape(snip.get('title', 'Wellness Video')),
                    channel=html.unescape(snip.get('channelTitle', '')),
                )
                if entry:
                    videos.append(entry)
        except Exception as e:
            logger.warning('YouTube API error for "%s": %s', query, e)
    return videos


def get_videos_for_emotion(emotion):
    queries = get_ai_search_queries(emotion)
    videos  = search_youtube_videos(queries)
    if len(videos) < TARGET_VIDEOS:
        existing = {v['video_id'] for v in videos}
        for fb in FALLBACK_VIDEOS.get(emotion, []):
            if fb['video_id'] not in existing:
                entry = _build_video_dict(fb['video_id'], fb['title'], fb['channel'])
                if entry:
                    videos.append(entry)
                    existing.add(fb['video_id'])
            if len(videos) >= TARGET_VIDEOS:
                break
    return videos[:TARGET_VIDEOS]


# ── 2FA helpers ───────────────────────────────────────────────────────────────

def _generate_code():
    return ''.join(random.choices(string.digits, k=6))


def _send_verification_email(user, code):
    send_mail(
        subject='Your Mind Companion verification code',
        message=(
            f'Hi {user.username},\n\n'
            f'Your verification code is: {code}\n\n'
            f'It expires in 10 minutes.\n\n— Mind Companion'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def _issue_code(user):
    EmailVerification.objects.filter(user=user, is_used=False).delete()
    code = _generate_code()
    EmailVerification.objects.create(user=user, code=code)
    return code


# ── Auth views ────────────────────────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect('wellness:landing')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Registration successful! Please log in to receive your 2FA verification code.'
            )
            return redirect('wellness:login')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('wellness:landing')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.email:
                # No email on account — skip 2FA and log straight in
                login(request, user)
                return _safe_redirect(request)
            try:
                code = _issue_code(user)
                _send_verification_email(user, code)
                # Code sent — park user id and redirect to verify page.
                # The user is NOT logged in yet at this point.
                request.session['2fa_user_id'] = user.pk
                request.session['2fa_next']    = request.GET.get('next', '')
                return redirect('wellness:verify_email')
            except Exception as e:
                # FAIL CLOSED — any error sending the 2FA code must NOT
                # log the user in. Re-render the login form with an error.
                logger.error('2FA send failed for %s (%s: %s)',
                             user.username, type(e).__name__, e)
                messages.error(
                    request,
                    'Unable to send 2FA verification code. Please try again later.'
                )
                return render(request, 'registration/login.html', {'form': form})
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


def _safe_redirect(request):
    next_url = request.GET.get('next', '')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect('wellness:landing')


def verify_email_view(request):
    user_id = request.session.get('2fa_user_id')
    if not user_id:
        return redirect('wellness:login')
    from django.contrib.auth.models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('wellness:login')
    parts  = user.email.split('@')
    masked = parts[0][:2] + '***@' + parts[1] if len(parts) == 2 else '***'
    if request.method == 'POST':
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            entered = form.cleaned_data['code'].strip()
            try:
                record = EmailVerification.objects.get(user=user, code=entered, is_used=False)
            except EmailVerification.DoesNotExist:
                form.add_error('code', 'Invalid code. Please try again.')
                return render(request, 'registration/verify_email.html',
                              {'form': form, 'masked_email': masked})
            if record.is_expired():
                form.add_error('code', 'This code has expired. Please log in again to get a new one.')
                return render(request, 'registration/verify_email.html',
                              {'form': form, 'masked_email': masked})
            record.is_used = True
            record.save()
            del request.session['2fa_user_id']
            next_url = request.session.pop('2fa_next', '')
            login(request, user)
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect('wellness:landing')
    else:
        form = VerifyCodeForm()
    return render(request, 'registration/verify_email.html',
                  {'form': form, 'masked_email': masked})


def resend_code_view(request):
    user_id = request.session.get('2fa_user_id')
    if not user_id:
        return redirect('wellness:login')
    from django.contrib.auth.models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('wellness:login')
    try:
        code = _issue_code(user)
        _send_verification_email(user, code)
        messages.success(request, 'A new code has been sent to your email.')
    except Exception as e:
        logger.error('Failed to resend 2FA email: %s', e)
        messages.error(request, 'Could not send email. Please try again.')
    return redirect('wellness:verify_email')


def logout_view(request):
    logout(request)
    return redirect('wellness:landing')


# ── Core wellness views ───────────────────────────────────────────────────────

def landing(request):
    return render(request, 'wellness/landing.html', {'emotions': EMOTION_META})


def recommendations(request, emotion):
    if emotion not in EMOTION_META:
        from django.http import Http404
        raise Http404('Unknown emotion')
    meta      = EMOTION_META[emotion]
    videos    = get_videos_for_emotion(emotion)
    video_ids = ','.join(v['video_id'] for v in videos)

    # Attach aggregate rating data — one DB query for all 6 videos
    rating_map = {
        row['video_id']: {
            'avg':   round(row['avg_score'], 1),
            'count': row['rating_count'],
        }
        for row in VideoRating.objects
            .filter(video_id__in=[v['video_id'] for v in videos])
            .values('video_id')
            .annotate(avg_score=Avg('score'), rating_count=Count('id'))
    }
    for v in videos:
        agg = rating_map.get(v['video_id'])
        v['avg_score']    = agg['avg']   if agg else None
        v['rating_count'] = agg['count'] if agg else 0

    if not request.session.session_key:
        request.session.create()
    request.session['last_emotion']   = emotion
    request.session['last_video_ids'] = video_ids
    return render(request, 'wellness/recommendations.html', {
        'emotion': emotion, 'meta': meta,
        'videos': videos, 'video_ids': video_ids, 'emotions': EMOTION_META,
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


def thank_you(request):
    emotion = request.GET.get('emotion', '')
    meta    = EMOTION_META.get(emotion, {})
    return render(request, 'wellness/thank_you.html', {
        'emotion': emotion, 'meta': meta, 'emotions': EMOTION_META,
    })


# ── Video feedback AJAX endpoints ─────────────────────────────────────────────

@require_POST
def video_rate(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    video_id    = data.get('video_id', '').strip()
    video_title = data.get('video_title', '').strip()[:255]
    score       = data.get('score')

    if not VIDEO_ID_RE.match(video_id):
        return JsonResponse({'error': 'Invalid video ID.'}, status=400)
    try:
        score = int(score)
        assert 1 <= score <= 5
    except (TypeError, ValueError, AssertionError):
        return JsonResponse({'error': 'Score must be 1–5.'}, status=400)

    if request.user.is_authenticated:
        obj, created = VideoRating.objects.update_or_create(
            user=request.user, video_id=video_id,
            defaults={'score': score, 'video_title': video_title},
        )
        message = 'Rating saved!' if created else 'Rating updated!'
    else:
        obj = VideoRating.objects.create(
            user=None, video_id=video_id,
            video_title=video_title, score=score,
        )
        message = 'Rating saved!'

    return JsonResponse({'success': True, 'score': obj.score, 'message': message})


@require_POST
def video_comment(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    video_id    = data.get('video_id', '').strip()
    video_title = data.get('video_title', '').strip()[:255]
    body        = data.get('body', '').strip()

    if not VIDEO_ID_RE.match(video_id):
        return JsonResponse({'error': 'Invalid video ID.'}, status=400)
    if not body:
        return JsonResponse({'error': 'Comment cannot be empty.'}, status=400)
    if len(body) > 500:
        return JsonResponse({'error': 'Max 500 characters.'}, status=400)

    user = request.user if request.user.is_authenticated else None
    comment = VideoComment.objects.create(
        user=user, video_id=video_id,
        video_title=video_title, body=body,
    )
    return JsonResponse({
        'success':  True,
        'username': user.username if user else 'Anonymous',
        'body':     comment.body,
        'time':     comment.created_at.strftime('%b %d, %Y'),
    })


@require_POST
def video_feedback(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    video_id = data.get('video_id', '').strip()
    if not VIDEO_ID_RE.match(video_id):
        return JsonResponse({'error': 'Invalid video ID.'}, status=400)

    comments = list(
        VideoComment.objects
        .filter(video_id=video_id)
        .order_by('-created_at')[:20]
        .values('user__username', 'body', 'created_at')
    )
    for c in comments:
        c['created_at'] = c['created_at'].strftime('%b %d, %Y')
        c['username']   = c.pop('user__username') or 'Anonymous'

    user_score = None
    if request.user.is_authenticated:
        try:
            user_score = VideoRating.objects.get(
                user=request.user, video_id=video_id
            ).score
        except VideoRating.DoesNotExist:
            pass

    agg = VideoRating.objects.filter(video_id=video_id).aggregate(
        avg=Avg('score'), count=Count('id')
    )
    return JsonResponse({
        'comments':     comments,
        'user_score':   user_score,
        'avg_score':    round(agg['avg'], 1) if agg['avg'] else None,
        'rating_count': agg['count'],
        'logged_in':    request.user.is_authenticated,
        'username':     request.user.username if request.user.is_authenticated else '',
    })


# ── User profile & watch history ──────────────────────────────────────────────

@login_required
def user_profile(request):
    """
    Personal dashboard showing the user's watch history, videos they rated
    highly (4–5 stars), and their comment history.
    """
    user = request.user

    # list() so the template can call |length without hitting the sliced-
    # queryset TypeError that auto_now_add fields can trigger.
    watch_history = list(
        WatchHistory.objects
        .filter(user=user)
        .order_by('-watched_at')
        .values('video_id', 'video_title', 'watched_at')[:50]
    )

    helpful_ratings = list(
        VideoRating.objects
        .filter(user=user, score__gte=4)
        .order_by('-updated_at')
    )

    comment_history = list(
        VideoComment.objects
        .filter(user=user)
        .order_by('-created_at')
    )

    return render(request, 'wellness/profile.html', {
        'watch_history':       watch_history,
        'helpful_ratings':     helpful_ratings,
        'comment_history':     comment_history,
        'watch_history_count': len(watch_history),
        'helpful_count':       len(helpful_ratings),
        'comment_count':       len(comment_history),
    })


@require_POST
def record_watch_history(request):
    """
    Silent AJAX endpoint called whenever a logged-in user opens a video modal.
    Anonymous visitors are ignored silently.

    Upsert logic — one row per (user, video_id):
      • Row exists  → update watched_at to now() so the video floats to the
                      top of the profile history list.
      • No row yet  → create it.
    The whole DB operation is wrapped in try/except so any unexpected error
    returns a clean JSON response instead of an unhandled exception.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': True})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    video_id    = data.get('video_id', '').strip()
    video_title = data.get('video_title', '').strip()[:255]

    if not VIDEO_ID_RE.match(video_id):
        return JsonResponse({'error': 'Invalid video ID.'}, status=400)

    try:
        WatchHistory.objects.update_or_create(
            user=request.user,
            video_id=video_id,
            defaults={
                'video_title': video_title,
                'watched_at':  timezone.now(),
            },
        )
    except Exception as e:
        logger.error('record_watch_history DB error for %s / %s: %s',
                     request.user.username, video_id, e)
        return JsonResponse({'error': 'Could not save watch history.'}, status=500)

    return JsonResponse({'success': True})


@login_required
@require_POST
def clear_watch_history(request):
    """
    Deletes all WatchHistory rows for the logged-in user and redirects back
    to their profile dashboard with a success message.
    Only accepts POST — the template uses a <form method="POST"> for CSRF safety.
    """
    WatchHistory.objects.filter(user=request.user).delete()
    messages.success(request, 'Your watch history has been securely cleared.')
    return redirect('wellness:profile')
