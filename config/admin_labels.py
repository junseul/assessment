"""Korean labels for the admin app/model list. Display only — no DB change."""
from types import MethodType

from django.contrib import admin
from django.urls import reverse

APP_NAMES = {
    'invites': '초대 관리',
    'traits': '성향파악',
    'games': '전략게임',
    'interviews': '영상면접',
    'auth': '계정',
}

MODEL_NAMES = {
    'Candidate': '지원자',
    'Invite': '초대 링크',
    'Survey': '설문',
    'SurveyResponse': '설문 응답',
    'GameResult': '게임 결과',
    'InterviewResponse': '면접 응답',
    'User': '사용자',
    'Group': '그룹',
}

MODEL_ORDER = {
    'auth': ['User', 'Group'],
}

# 사이드바 앱 표시 순서. 여기 없는 앱은 기본 순서를 유지한 채 뒤에 붙는다.
APP_ORDER = ['auth', 'invites', 'traits', 'games', 'interviews']

MODEL_ORDER = {
    'auth': ['User', 'Group'],
}

_original_get_app_list = admin.AdminSite.get_app_list


class AdminTitleMixin:
    """체인지리스트 상단 '변경할 <모델명> 선택' 타이틀을 한글로 고정한다.

    Django 기본 타이틀은 영문 모델명을 그대로 노출하므로(예: '변경할 candidate
    선택'), 각 ModelAdmin에서 changelist_title만 지정해 화면 문구만 바꾼다."""

    changelist_title = None

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        if self.changelist_title and getattr(response, 'context_data', None):
            response.context_data['title'] = self.changelist_title
        return response


def _results_analysis_app():
    """사이드바 '결과 분석' 섹션 — 지원자 리포트(전체 결과)로 연결."""
    report_url = reverse('reports:candidate_list')
    return {
        'app_label': 'results-analysis',
        'name': '결과 분석',
        'app_url': report_url,
        'models': [
            {
                'name': '지원자 리포트',
                'object_name': 'CandidateReport',
                'admin_url': report_url,
                'add_url': None,
            }
        ],
    }


def _get_app_list(self, request, app_label=None):
    app_list = _original_get_app_list(self, request, app_label)
    for app in app_list:
        if app.get('app_label') in APP_NAMES:
            app['name'] = APP_NAMES[app['app_label']]
        order = MODEL_ORDER.get(app.get('app_label'))
        if order:
            rank = {name: idx for idx, name in enumerate(order)}
            app['models'].sort(key=lambda m: rank.get(m.get('object_name'), len(rank)))
        for model in app.get('models', []):
            object_name = model.get('object_name')
            if object_name in MODEL_NAMES:
                model['name'] = MODEL_NAMES[object_name]
            model_admin = self._registry.get(model.get('model'))
            if model_admin:
                model['count'] = model_admin.get_queryset(request).count()
    # 사이드바(전체 목록)에서만 순서를 제어한다. APP_ORDER대로 정렬한 뒤
    # '결과 분석' 섹션을 앱 목록 맨 뒤(로컬 테스트 모듈 바로 위)에 배치한다.
    if app_label is None:
        order_index = {name: i for i, name in enumerate(APP_ORDER)}
        app_list.sort(key=lambda app: order_index.get(app.get('app_label'), len(APP_ORDER)))
        app_list.append(_results_analysis_app())
    return app_list


admin.site.get_app_list = MethodType(_get_app_list, admin.site)
