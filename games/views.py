import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.shortcuts import render

from invites.decorators import candidate_required

from .models import GameResult


@candidate_required
def go_nogo(request):
    return render(request, 'games/go_nogo.html', {
        'candidate_name': request.session.get('candidate_name'),
        'already_done': (
            not request.session.get('local_test_mode')
            and GameResult.objects.filter(candidate=request.candidate).exists()
        ),
    })


@candidate_required
@require_POST
def submit_result(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest('invalid json')

    trials = payload.get('trials')
    summary = payload.get('summary')
    if not isinstance(trials, list) or not isinstance(summary, dict):
        return HttpResponseBadRequest('trials and summary are required')

    if request.session.get('local_test_mode'):
        return JsonResponse({'ok': True, 'local_test': True})

    if GameResult.objects.filter(candidate=request.candidate, game_slug='go-nogo').exists():
        return JsonResponse({'ok': True, 'already_submitted': True}, status=409)

    GameResult.objects.create(
        game_slug='go-nogo',
        candidate=request.candidate,
        respondent_email=request.candidate.email,
        trials=trials,
        summary=summary,
    )
    return JsonResponse({'ok': True})
