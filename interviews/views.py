import logging

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from invites.decorators import candidate_required

from .models import InterviewResponse, DEFAULT_QUESTION

logger = logging.getLogger(__name__)

DEEPSEEK_SYSTEM_PROMPT = (
    '당신은 채용 면접관입니다. 지원자의 자기소개 답변을 읽고, '
    '답변 내용에 기반한 구체적인 후속 질문을 한국어로 1개만 생성하세요. '
    '질문 문장만 출력하고 다른 설명은 붙이지 마세요.'
)

MAX_INTERVIEW_VIDEO_BYTES = 100 * 1024 * 1024
ALLOWED_VIDEO_EXTENSIONS = {'.webm', '.mp4', '.ogg', '.mov'}


def generate_followup_question(transcript):
    """Ask DeepSeek for one follow-up question grounded in the candidate's answer.
    Returns '' on any API failure so the interview submission never blocks on this."""
    if not transcript.strip() or not settings.DEEPSEEK_API_KEY:
        return ''
    try:
        resp = requests.post(
            'https://api.deepseek.com/chat/completions',
            headers={
                'Authorization': f'Bearer {settings.DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'deepseek-v4-flash',
                'messages': [
                    {'role': 'system', 'content': DEEPSEEK_SYSTEM_PROMPT},
                    {'role': 'user', 'content': transcript},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()['choices'][0]['message']['content'].strip()
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning('DeepSeek follow-up failed: %s', exc)
        return ''


def _is_allowed_video(uploaded):
    name = (uploaded.name or '').lower()
    ext = name[name.rfind('.'):] if '.' in name else ''
    content_type = (uploaded.content_type or '').lower()
    type_ok = content_type.startswith('video/') or ext in ALLOWED_VIDEO_EXTENSIONS
    return type_ok and 0 < uploaded.size <= MAX_INTERVIEW_VIDEO_BYTES


@candidate_required
@xframe_options_sameorigin
def interview_detail(request):
    existing = None if request.session.get('local_test_mode') else (
        InterviewResponse.objects
        .filter(candidate=request.candidate)
        .order_by('-created_at')
        .first()
    )
    return render(request, 'interviews/interview_detail.html', {
        'question': DEFAULT_QUESTION,
        'candidate_name': request.session.get('candidate_name'),
        'already_done': existing is not None and (
            not existing.follow_up_question or bool(existing.follow_up_submitted_at)
        ),
        'existing': existing,
        'has_first_response': existing is not None,
        'existing_follow_up': existing.follow_up_question if existing else '',
    })


@candidate_required
@require_POST
def submit_response(request):
    transcript = request.POST.get('transcript', '')
    video = request.FILES.get('video')
    local_test = request.session.get('local_test_mode')
    if not local_test and InterviewResponse.objects.filter(candidate=request.candidate).exists():
        existing = InterviewResponse.objects.filter(candidate=request.candidate).order_by('-created_at').first()
        return JsonResponse({
            'ok': True,
            'already_submitted': True,
            'follow_up_question': existing.follow_up_question if existing else '',
        }, status=409)

    if not video:
        return HttpResponseBadRequest('video is required')
    if not _is_allowed_video(video):
        return HttpResponseBadRequest('invalid video')

    follow_up = generate_followup_question(transcript)

    if local_test:
        follow_up = follow_up or '답변에서 가장 중요했던 판단과 그 이유를 구체적으로 설명해 주세요.'
        return JsonResponse({
            'ok': True, 'local_test': True, 'response_id': 0,
            'follow_up_question': follow_up,
        })

    response = InterviewResponse.objects.create(
        candidate=request.candidate,
        respondent_email=request.candidate.email,
        transcript=transcript,
        video=video,
        follow_up_question=follow_up,
    )
    return JsonResponse({'ok': True, 'response_id': response.pk, 'follow_up_question': follow_up})


@candidate_required
@require_POST
def submit_follow_up(request, pk):
    local_test = request.session.get('local_test_mode')
    response = None if local_test else get_object_or_404(
        InterviewResponse, pk=pk, candidate=request.candidate,
    )
    if local_test:
        transcript = request.POST.get('transcript', '').strip()
        video = request.FILES.get('video')
        if not transcript or not video:
            return HttpResponseBadRequest('transcript and video are required')
        if not _is_allowed_video(video):
            return HttpResponseBadRequest('invalid video')
        return JsonResponse({'ok': True, 'local_test': True})
    if response.follow_up_submitted_at:
        return JsonResponse({'ok': True, 'already_submitted': True}, status=409)

    transcript = request.POST.get('transcript', '').strip()
    video = request.FILES.get('video')
    if not transcript or not video:
        return HttpResponseBadRequest('transcript and video are required')
    if not _is_allowed_video(video):
        return HttpResponseBadRequest('invalid video')

    response.follow_up_transcript = transcript
    response.follow_up_video = video
    response.follow_up_submitted_at = timezone.now()
    response.save(update_fields=['follow_up_transcript', 'follow_up_video', 'follow_up_submitted_at'])
    return JsonResponse({'ok': True})


@login_required
def serve_video(request, pk):
    obj = get_object_or_404(InterviewResponse, pk=pk)
    if not obj.video:
        raise Http404
    return FileResponse(obj.video.open('rb'))


@login_required
def serve_follow_up_video(request, pk):
    obj = get_object_or_404(InterviewResponse, pk=pk)
    if not obj.follow_up_video:
        raise Http404
    return FileResponse(obj.follow_up_video.open('rb'))
