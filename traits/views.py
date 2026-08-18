import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from invites.decorators import candidate_required

from .models import Survey, SurveyResponse
from .survey_definition import QUESTION_TEXT


@candidate_required
@xframe_options_sameorigin
def survey_detail(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    return render(request, 'traits/survey_detail.html', {
        'survey': survey,
        'candidate_name': request.session.get('candidate_name'),
        'already_done': (
            not request.session.get('local_test_mode')
            and SurveyResponse.objects.filter(survey=survey, candidate=request.candidate).exists()
        ),
    })


@candidate_required
@require_POST
def submit_response(request, pk):
    survey = get_object_or_404(Survey, pk=pk)
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest('invalid json')

    answers = payload.get('answers')
    if not isinstance(answers, dict):
        return HttpResponseBadRequest('answers is required')
    expected = {f'q{number:03d}' for number in range(1, len(QUESTION_TEXT) + 1)}

    def is_valid_entry(entry):
        if not isinstance(entry, dict) or set(entry) != {'value', 'rt_ms', 'timed_out', 'seq'}:
            return False
        value = entry['value']
        value_ok = value is None or (isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5)
        rt_ms = entry['rt_ms']
        rt_ok = isinstance(rt_ms, int) and not isinstance(rt_ms, bool) and rt_ms >= 0
        timed_out_ok = isinstance(entry['timed_out'], bool) and entry['timed_out'] == (value is None)
        seq = entry['seq']
        seq_ok = isinstance(seq, int) and not isinstance(seq, bool) and 0 <= seq < len(QUESTION_TEXT)
        return value_ok and rt_ok and timed_out_ok and seq_ok

    seqs_ok = {entry['seq'] for entry in answers.values() if isinstance(entry, dict) and 'seq' in entry} \
        == set(range(len(QUESTION_TEXT)))
    if set(answers) != expected or not seqs_ok or any(not is_valid_entry(entry) for entry in answers.values()):
        return HttpResponseBadRequest('invalid answers')

    if request.session.get('local_test_mode'):
        return JsonResponse({'ok': True, 'local_test': True})

    if SurveyResponse.objects.filter(survey=survey, candidate=request.candidate).exists():
        return JsonResponse({'ok': True, 'already_submitted': True}, status=409)

    SurveyResponse.objects.create(
        survey=survey,
        candidate=request.candidate,
        respondent_email=request.candidate.email,
        answers=answers,
    )
    return JsonResponse({'ok': True})
