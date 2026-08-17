from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from games.models import GameResult
from interviews.models import InterviewResponse
from traits.models import Survey, SurveyResponse

from .decorators import candidate_required
from .forms import VerifyForm, digits_only
from .models import Candidate, Invite


@staff_member_required
def local_test(request, stage):
    if not settings.DEBUG:
        raise Http404

    candidate = Candidate.objects.order_by('-created_at').first()
    if candidate is None:
        raise Http404('테스트할 지원자가 없습니다.')
    request.session['candidate_id'] = candidate.pk
    request.session['candidate_name'] = candidate.name
    request.session['candidate_email'] = candidate.email
    request.session['local_test_mode'] = True

    if stage == 'traits':
        survey = Survey.objects.order_by('id').first()
        if survey is None:
            raise Http404('테스트할 설문이 없습니다.')
        return redirect('traits:survey_detail', pk=survey.pk)
    if stage == 'games':
        return redirect('games:go_nogo')
    if stage == 'interviews':
        return redirect('interviews:interview_detail')
    raise Http404


def verify(request, token):
    invite = get_object_or_404(Invite, token=token)

    if request.method == 'POST':
        form = VerifyForm(request.POST)
        if form.is_valid():
            c = invite.candidate
            matches = (
                form.cleaned_data['name'] == c.name.strip()
                and form.cleaned_data['birthdate'] == c.birthdate
                and digits_only(form.cleaned_data['phone']) == digits_only(c.phone)
            )
            if matches:
                # used_at is an audit stamp. The same candidate may re-verify
                # (lost session, resume) so do not overwrite the first use time.
                if invite.used_at is None:
                    invite.used_at = timezone.now()
                    invite.save(update_fields=['used_at'])
                request.session.cycle_key()
                request.session['candidate_id'] = c.id
                request.session['candidate_name'] = c.name
                request.session['candidate_email'] = c.email
                request.session.pop('local_test_mode', None)
                return redirect('invites:start')
            form.add_error(None, '입력하신 정보가 등록된 정보와 일치하지 않습니다.')
    else:
        form = VerifyForm()

    return render(request, 'invites/verify.html', {'form': form})


def no_access(request):
    return render(request, 'invites/no_access.html', status=403)


@candidate_required
def start(request):
    survey = Survey.objects.order_by('id').first()
    if survey:
        survey_done = SurveyResponse.objects.filter(survey=survey, candidate=request.candidate).exists()
    else:
        survey_done = SurveyResponse.objects.filter(candidate=request.candidate).exists()
    game_done = GameResult.objects.filter(candidate=request.candidate).exists()
    interview = InterviewResponse.objects.filter(candidate=request.candidate).order_by('-created_at').first()
    interview_done = bool(interview) and (
        not interview.follow_up_question or bool(interview.follow_up_submitted_at)
    )
    if survey and not survey_done:
        return redirect('traits:survey_detail', pk=survey.pk)
    if not game_done:
        return redirect('games:go_nogo')
    if not interview_done:
        return redirect('interviews:interview_detail')
    return render(request, 'invites/start.html', {
        'candidate_name': request.session.get('candidate_name'),
        'survey': survey,
        'survey_done': survey_done,
        'game_done': game_done,
        'interview_done': interview_done,
    })
