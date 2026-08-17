import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST
from django.shortcuts import render

from invites.decorators import candidate_required

from .catalog import GAMES, get_game
from .models import GameResult


@staff_member_required
@xframe_options_sameorigin
def admin_grid(request):
    """3x3 icon grid for admins to pick which game to test. Loaded inside the
    /admin/ local-test iframe (invites.views.local_test), so it stays
    unstyled/standalone rather than extending the candidate base.html."""
    return render(request, 'games/admin_grid.html', {'games': GAMES})


@candidate_required
def index(request):
    done_slugs = set(
        GameResult.objects.filter(candidate=request.candidate).values_list('game_slug', flat=True)
    )
    games = [dict(g, done=g['slug'] in done_slugs) for g in GAMES]
    return render(request, 'games/index.html', {
        'candidate_name': request.session.get('candidate_name'),
        'games': games,
    })


@candidate_required
@xframe_options_sameorigin
def play(request, slug):
    game = get_game(slug)
    if game is None or not game['implemented']:
        raise Http404

    already_done = (
        not request.session.get('local_test_mode')
        and GameResult.objects.filter(candidate=request.candidate, game_slug=slug).exists()
    )
    return render(request, game['template'], {
        'candidate_name': request.session.get('candidate_name'),
        'already_done': already_done,
        'slug': slug,
    })


@candidate_required
@require_POST
def submit_result(request, slug):
    game = get_game(slug)
    if game is None or not game['implemented']:
        return HttpResponseBadRequest('unknown game')

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

    if GameResult.objects.filter(candidate=request.candidate, game_slug=slug).exists():
        return JsonResponse({'ok': True, 'already_submitted': True}, status=409)

    GameResult.objects.create(
        game_slug=slug,
        candidate=request.candidate,
        respondent_email=request.candidate.email,
        trials=trials,
        summary=summary,
    )
    return JsonResponse({'ok': True})
