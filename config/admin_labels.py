"""Korean labels for the admin app/model list. Display only — no DB change."""
from types import MethodType

from django.contrib import admin

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

_original_get_app_list = admin.AdminSite.get_app_list


def _get_app_list(self, request, app_label=None):
    app_list = _original_get_app_list(self, request, app_label)
    for app in app_list:
        if app.get('app_label') in APP_NAMES:
            app['name'] = APP_NAMES[app['app_label']]
        for model in app.get('models', []):
            object_name = model.get('object_name')
            if object_name in MODEL_NAMES:
                model['name'] = MODEL_NAMES[object_name]
            model_admin = self._registry.get(model.get('model'))
            if model_admin:
                model['count'] = model_admin.get_queryset(request).count()
    return app_list


admin.site.get_app_list = MethodType(_get_app_list, admin.site)
