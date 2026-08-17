from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from games.models import GameResult
from interviews.models import InterviewResponse
from invites.models import Candidate
from traits.models import SurveyResponse
from traits.survey_definition import score_answers


@login_required
def candidate_list(request):
    candidates = Candidate.objects.order_by('-created_at')
    return render(request, 'reports/candidate_list.html', {'candidates': candidates})


@login_required
def candidate_detail(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    survey_responses = list(
        SurveyResponse.objects.filter(candidate=candidate).select_related('survey').order_by('-created_at')
    )
    for response in survey_responses:
        response.domain_scores = score_answers(response.answers)
        ratings = [item['score'] for item in response.domain_scores if item['score'] is not None]
        response.score = round(sum(ratings) / len(ratings), 1) if ratings else None
        response.interpretation = (
            '강점 수준' if response.score is not None and response.score >= 75
            else '보통 수준' if response.score is not None and response.score >= 50
            else '개발 필요' if response.score is not None
            else '점수 문항 없음'
        )
    game_results = list(GameResult.objects.filter(candidate=candidate).order_by('-created_at'))
    for result in game_results:
        accuracy = result.summary.get('accuracy')
        result.interpretation = (
            '정확한 반응 억제' if isinstance(accuracy, (int, float)) and accuracy >= .9
            else '대체로 안정적' if isinstance(accuracy, (int, float)) and accuracy >= .75
            else '오반응 검토 필요' if isinstance(accuracy, (int, float))
            else '해석 불가'
        )
    interview_responses = list(InterviewResponse.objects.filter(candidate=candidate).order_by('-created_at'))
    interview_complete = bool(interview_responses) and (
        not interview_responses[0].follow_up_question
        or bool(interview_responses[0].follow_up_submitted_at)
    )
    context = {
        'email': candidate.email,
        'candidate': candidate,
        'survey_responses': survey_responses,
        'game_results': game_results,
        'interview_responses': interview_responses,
        'survey_complete': bool(survey_responses),
        'game_complete': bool(game_results),
        'interview_complete': interview_complete,
    }
    return render(request, 'reports/candidate_detail.html', context)
