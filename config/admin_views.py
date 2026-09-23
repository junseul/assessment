"""관리 대시보드(/admin/) 기간 조회 뷰. 표시 전용 — DB 구조 변경 없음."""
import datetime

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from config.admin_labels import MODEL_NAMES

# 대시보드 통계에 표시되는 모델과 사용할 날짜 필드
PERIOD_MODELS = [
    ('Candidate', 'created_at'),
    ('Invite', 'created_at'),
    ('SurveyResponse', 'created_at'),
    ('GameResult', 'created_at'),
    ('InterviewResponse', 'created_at'),
]

DATE_ERROR = '날짜 형식이 올바르지 않습니다. yyyymmdd 또는 yymmdd로 입력하세요.'
ORDER_ERROR = '시작일이 종료일보다 늦을 수 없습니다.'


def parse_query_date(value):
    """yyyymmdd 또는 yymmdd(20xx) 문자열을 date로 변환. 실패 시 ValueError."""
    value = value.strip()
    if not value.isdigit() or len(value) not in (6, 8):
        raise ValueError(value)
    if len(value) == 8:
        year, month, day = int(value[:4]), int(value[4:6]), int(value[6:8])
    else:
        year, month, day = 2000 + int(value[:2]), int(value[2:4]), int(value[4:6])
    return datetime.date(year, month, day)


def dashboard_index(request):
    today = timezone.localdate()
    default_start = today.replace(month=1, day=1)

    start_raw = request.GET.get('start', '').strip()
    end_raw = request.GET.get('end', '').strip()

    start_value = start_raw or default_start.strftime('%Y%m%d')
    end_value = end_raw or today.strftime('%Y%m%d')

    error = None
    start_date = end_date = None
    try:
        start_date = parse_query_date(start_value)
        end_date = parse_query_date(end_value)
        if start_date > end_date:
            error = ORDER_ERROR
    except ValueError:
        error = DATE_ERROR

    period_results = []
    if error is None:
        for object_name, field_name in PERIOD_MODELS:
            model = next(
                (m for m in admin.site._registry
                 if m._meta.object_name == object_name),
                None,
            )
            count = 0
            url = None
            if model is not None:
                count = model.objects.filter(
                    **{f'{field_name}__date__gte': start_date,
                       f'{field_name}__date__lte': end_date}
                ).count()
                try:
                    url = reverse(
                        'admin:%s_%s_changelist'
                        % (model._meta.app_label, model._meta.model_name)
                    )
                except NoReverseMatch:
                    url = None
            period_results.append({
                'label': MODEL_NAMES.get(object_name, object_name),
                'count': count,
                'url': url,
            })
    extra_context = {
        'period_start': start_value,
        'period_end': end_value,
        'period_range_text': f'{start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}' if error is None else '',
        'period_error': error,
        'period_results': period_results,
    }
    return admin.site.index(request, extra_context=extra_context)

def results_analysis_dashboard(request):
    report_url = reverse('reports:candidate_list')
    model_specs = [
        ('Candidate', '지원자 리포트', report_url),
        ('SurveyResponse', '성향파악 결과', None),
        ('GameResult', '전략게임 결과', None),
        ('InterviewResponse', '영상면접 결과', None),
    ]
    stats = []
    for object_name, label, fixed_url in model_specs:
        model = next(
            (registered for registered in admin.site._registry
             if registered._meta.object_name == object_name),
            None,
        )
        url = fixed_url
        if model is not None and url is None:
            url = reverse(
                f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist'
            )
        stats.append({
            'label': label,
            'count': model.objects.count() if model is not None else 0,
            'url': url,
        })
    context = {
        **admin.site.each_context(request),
        'title': '결과 분석 관리 대시보드',
        'dashboard_title': '결과 분석 관리 대시보드',
        'dashboard_description': '지원자별 검사 결과와 종합 리포트를 확인합니다.',
        'result_stats': stats,
        'report_url': report_url,
    }
    return TemplateResponse(request, 'admin/results_analysis_dashboard.html', context)
