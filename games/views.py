import json
import random

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST
from django.shortcuts import render

from invites.decorators import candidate_required

from .catalog import GAMES, get_game
from .models import GameResult

# expedition-investment (전략게임) payoff table. Kept server-side only: if this
# shipped to the client (as it used to, inline in the page's <script>), anyone
# could read exact win/loss odds from devtools and solve the task instead of
# playing it under genuine uncertainty, which is the thing being measured.
EXPEDITION_TRIALS = 100
EXPEDITION_REVERSAL_INDEX = 50
EXPEDITION_BASE_DECKS = {
    'A': {'win_amt': 100, 'loss_prob': 0.5, 'loss_amt': 250},
    'B': {'win_amt': 100, 'loss_prob': 0.1, 'loss_amt': 1250},
    'C': {'win_amt': 50, 'loss_prob': 0.5, 'loss_amt': 25},
    'D': {'win_amt': 50, 'loss_prob': 0.1, 'loss_amt': 125},
}
EXPEDITION_REVERSAL_MAP = {'A': 'C', 'B': 'D', 'C': 'A', 'D': 'B'}


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
    if slug == 'expedition-investment' and not already_done:
        request.session['expedition_state'] = {'trial_index': 0, 'running_total': 0}
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

    trials = payload.get('trials') if isinstance(payload, dict) else None
    summary = payload.get('summary') if isinstance(payload, dict) else None
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


@candidate_required
@require_POST
def expedition_round(request):
    """Resolves one expedition-investment deck pick server-side so the payoff
    table and reversal point never reach the client. See EXPEDITION_* above."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest('invalid json')
    if not isinstance(payload, dict):
        return HttpResponseBadRequest('invalid payload')

    deck_choice = payload.get('deck')
    if deck_choice not in EXPEDITION_BASE_DECKS:
        return HttpResponseBadRequest('invalid deck')

    state = request.session.get('expedition_state') or {'trial_index': 0, 'running_total': 0}
    trial_index = state['trial_index']
    if trial_index >= EXPEDITION_TRIALS:
        return HttpResponseBadRequest('game already complete')

    reversed_phase = trial_index >= EXPEDITION_REVERSAL_INDEX
    source_letter = EXPEDITION_REVERSAL_MAP[deck_choice] if reversed_phase else deck_choice
    deck = EXPEDITION_BASE_DECKS[source_letter]

    is_loss = random.random() < deck['loss_prob']
    amount = deck['win_amt'] - (deck['loss_amt'] if is_loss else 0)
    running_total = state['running_total'] + amount

    state['trial_index'] = trial_index + 1
    state['running_total'] = running_total
    request.session['expedition_state'] = state

    return JsonResponse({
        'deck': deck_choice,
        'amount': amount,
        'is_loss': is_loss,
        'running_total': running_total,
        'trial_index': trial_index,
        'phase': 'post' if reversed_phase else 'pre',
    })
