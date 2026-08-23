from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from games.catalog import GAMES
from games.models import GameResult
from interviews.models import InterviewResponse
from invites.models import Candidate
from traits.models import SurveyResponse
from traits.survey_definition import response_quality, score_answers

# 각 게임의 summary에 저장된 키를 리포트 표시 라벨로 매핑한다. 게임별 측정
# 지표가 서로 달라, 공통 키(accuracy/avg_rt_ms/n_trials)만 가정하면 대부분
# 게임의 지표가 빈칸으로 남는다.
GAME_METRICS = {
    'radar-control': [
        ('정확도', 'accuracy'),
        ('평균 반응시간(ms)', 'mean_rt_ms'),
        ('반응시간 표준편차(ms)', 'rt_sd_ms'),
        ('누락 오류율', 'omission_error_rate'),
        ('오반응(오경보)율', 'commission_error_rate'),
        ('시행 수', 'n_trials'),
    ],
    'emergency-brake': [
        ('GO 평균 반응시간(ms)', 'mean_go_rt_ms'),
        ('GO 반응시간 중앙값(ms)', 'median_go_rt_ms'),
        ('GO 누락률', 'go_miss_rate'),
        ('조기 반응 횟수', 'premature_response_count'),
        ('정지 신호 성공률', 'stop_success_rate'),
        ('평균 SSD(ms)', 'mean_ssd_ms'),
        ('SSRT(ms)', 'ssrt_ms'),
        ('시행 수', 'n_trials'),
    ],
    'sorting-center': [
        ('반복 시행 반응시간(ms)', 'repeat_rt_ms'),
        ('전환 시행 반응시간(ms)', 'switch_rt_ms'),
        ('전환 비용(ms)', 'switch_cost_ms'),
        ('전환 오류율', 'switch_error_rate'),
        ('반복 오류율', 'repeat_error_rate'),
        ('고집 오류 횟수', 'perseverative_error_count'),
        ('시행 수', 'n_trials'),
    ],
    'space-station-schedule': [
        ('점검 정확도', 'ongoing_accuracy'),
        ('점검 평균 반응시간(ms)', 'ongoing_mean_rt_ms'),
        ('사건 약속 정확도', 'event_pm_accuracy'),
        ('시간 약속 정확도', 'time_pm_accuracy'),
        ('전체 약속 정확도', 'overall_pm_accuracy'),
        ('평균 타이밍 오차(ms)', 'mean_timing_error_ms'),
        ('조기 약속 반응 횟수', 'premature_pm_response_count'),
    ],
    'drone-tracking': [
        ('추적 정확도', 'tracking_accuracy'),
        ('추적 용량', 'tracking_capacity'),
        ('최종 표적 수', 'ending_n_targets'),
        ('시행 수', 'n_trials'),
    ],
    'quality-inspector': [
        ('정확도', 'accuracy'),
        ('평균 탐색 반응시간(ms)', 'mean_search_rt_ms'),
        ('불량 누락률', 'miss_rate'),
        ('오경보율', 'false_alarm_rate'),
        ('탐색 기울기(ms/개)', 'search_slope_ms_per_item'),
        ('시행 수', 'n_trials'),
    ],
    'cipher-lab': [
        ('정확도', 'accuracy'),
        ('평균 반응시간(ms)', 'mean_rt_ms'),
        ('복잡도 임계값', 'complexity_threshold'),
        ('시행 수', 'n_trials'),
    ],
    'flash-comm': [
        ('첫 번째 신호 정확도', 't1_accuracy'),
        ('두 번째 신호 정확도', 't2_accuracy'),
        ('T1 정확 시 T2 정확도', 't2_given_t1_accuracy'),
        ('주의 깜빡임 회복 지연', 'attentional_blink_recovery_lag'),
        ('시퀀스 수', 'n_sequences'),
    ],
    'expedition-investment': [
        ('최종 자원', 'final_total'),
        ('시행 수', 'n_trials'),
        ('탐색 비율', 'exploration_rate'),
        ('학습 기울기', 'learning_rate'),
        ('손실 후 동일선택 비율', 'loss_stay_rate'),
        ('반전 적응도', 'reversal_adaptation'),
        ('결과 변동성(위험선호)', 'outcome_variance'),
        ('손실추격 지수', 'loss_chasing_index'),
    ],
}

# 등록되지 않은 slug(테스트용 go-nogo 등)를 위한 기존 범용 폴백.
GENERIC_METRICS = [
    ('정확도', 'accuracy'),
    ('평균 반응시간(ms)', 'avg_rt_ms'),
    ('시행 수', 'n_trials'),
]


def _metric_value(result, key):
    if result.game_slug == 'space-station-schedule' and key == 'n_trials':
        return len([
            t for t in result.trials
            if isinstance(t, dict) and t.get('trial_stage') == 'ongoing'
        ]) or None
    return result.summary.get(key)


def _build_game_metrics(result):
    labels = GAME_METRICS.get(result.game_slug, GENERIC_METRICS)
    if result.game_slug == 'space-station-schedule':
        labels = list(labels)
        labels.append(('시행 수', 'n_trials'))
    metrics = []
    for label, key in labels:
        value = _metric_value(result, key)
        metrics.append((label, None if value is None else str(value)))
    return metrics


def _build_game_interpretation(result):
    s = result.summary
    slug = result.game_slug

    if slug == 'expedition-investment':
        exploration_rate = s.get('exploration_rate')
        if isinstance(exploration_rate, (int, float)):
            if exploration_rate >= .5:
                return f'탐색 위주 ({round(exploration_rate * 100)}% 탐색)'
            return f'활용 위주 ({round((1 - exploration_rate) * 100)}% 활용)'
        return '해석 불가'

    accuracy = s.get('accuracy')
    if isinstance(accuracy, (int, float)):
        if accuracy >= .9:
            return '정확한 반응 억제'
        if accuracy >= .75:
            return '대체로 안정적'
        return '오반응 검토 필요'

    stop_rate = s.get('stop_success_rate')
    if isinstance(stop_rate, (int, float)):
        if stop_rate >= .8:
            return '억제 성공률 높음'
        if stop_rate >= .5:
            return '억제 성공률 보통'
        return '억제 실패 다수'

    ongoing_acc = s.get('ongoing_accuracy')
    if isinstance(ongoing_acc, (int, float)):
        if ongoing_acc >= .9:
            return '점검 정확도 높음'
        if ongoing_acc >= .75:
            return '점검 정확도 보통'
        return '점검 오류 다수'

    tracking_acc = s.get('tracking_accuracy')
    if isinstance(tracking_acc, (int, float)):
        if tracking_acc >= .9:
            return '추적 정확도 우수'
        if tracking_acc >= .75:
            return '추적 정확도 보통'
        return '추적 정확도 개선 필요'

    switch_err = s.get('switch_error_rate')
    if isinstance(switch_err, (int, float)):
        if switch_err <= .1:
            return '규칙 전환 안정적'
        if switch_err <= .25:
            return '규칙 전환 보통'
        return '규칙 전환 오류 다수'

    t2_acc = s.get('t2_accuracy')
    if isinstance(t2_acc, (int, float)):
        if t2_acc >= .75:
            return '신호 회상 정확도 우수'
        if t2_acc >= .5:
            return '신호 회상 정확도 보통'
        return '신호 회상 개선 필요'

    return '해석 불가'


@login_required
def candidate_list(request):
    candidates = Candidate.objects.order_by('-created_at')
    return render(request, 'reports/candidate_list.html', {
        **admin.site.each_context(request),
        'title': '지원자 리포트',
        'candidates': candidates,
    })


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
        response.quality = response_quality(response.answers)
    game_results = list(GameResult.objects.filter(candidate=candidate).order_by('-created_at'))
    done_slugs = {r.game_slug for r in game_results}
    # 9개 전략게임 각각의 완료 여부 — 일부만 완료해도 '완료'로 뭉뚱그리지 않는다.
    game_statuses = [
        {'slug': g['slug'], 'title': g['title'], 'done': g['slug'] in done_slugs}
        for g in GAMES if g['implemented']
    ]
    for result in game_results:
        result.metrics = _build_game_metrics(result)
        result.interpretation = _build_game_interpretation(result)
    interview_responses = list(InterviewResponse.objects.filter(candidate=candidate).order_by('-created_at'))
    interview_complete = bool(interview_responses) and (
        not interview_responses[0].follow_up_question
        or bool(interview_responses[0].follow_up_submitted_at)
    )
    context = {
        **admin.site.each_context(request),
        'title': f'{candidate.name} 리포트',
        'email': candidate.email,
        'candidate': candidate,
        'survey_responses': survey_responses,
        'game_results': game_results,
        'game_statuses': game_statuses,
        'interview_responses': interview_responses,
        'survey_complete': bool(survey_responses),
        'game_complete': bool(game_results),
        'interview_complete': interview_complete,
    }
    return render(request, 'reports/candidate_detail.html', context)
