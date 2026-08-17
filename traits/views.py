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
    if set(answers) != expected or any(
        value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5)
        for value in answers.values()
    ):
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
