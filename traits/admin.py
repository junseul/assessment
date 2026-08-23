import json
import logging
import urllib.parse

import requests
from django.conf import settings
from django.contrib import admin
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.urls import path

from config.admin_labels import AdminTitleMixin

from .item_review import (
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    build_item_review_prompt,
    survey_items,
)
from .models import Survey, SurveyResponse
from .survey_definition import DOMAINS, QUESTION_TEXT, REVERSED, response_quality, score_answers

logger = logging.getLogger(__name__)

VALUE_LABELS = {
    1: '전혀 그렇지 않다',
    2: '그렇지 않은 편이다',
    3: '보통이다',
    4: '그런 편이다',
    5: '매우 그렇다',
}


def _answer_detail(entry):
    if isinstance(entry, dict):
        value = entry.get('value')
        return {
            'value': value if isinstance(value, (int, float)) else None,
            'value_label': VALUE_LABELS.get(value, '-'),
            'rt_ms': entry.get('rt_ms'),
            'timed_out': bool(entry.get('timed_out')),
        }
    return {
        'value': entry if isinstance(entry, (int, float)) else None,
        'value_label': VALUE_LABELS.get(entry, '-'),
        'rt_ms': None,
        'timed_out': False,
    }


def _result_context(answers):
    domain_scores = score_answers(answers)
    has_domain_answers = any(d.get('answered') for d in domain_scores)

    quality = response_quality(answers)
    quality['fast_response_pct'] = (
        round(quality['fast_response_rate'] * 100, 1)
        if quality['fast_response_rate'] is not None else None
    )
    quality['extreme_response_pct'] = (
        round(quality['extreme_response_rate'] * 100, 1)
        if quality['extreme_response_rate'] is not None else None
    )

    domains_detail = []
    generic_answers = []
    if has_domain_answers:
        for key, label, start, end in DOMAINS:
            items = []
            for number in range(start, end + 1):
                entry = answers.get(f'q{number:03d}')
                items.append({
                    'number': number,
                    'text': QUESTION_TEXT[number - 1],
                    'reversed': number in REVERSED,
                    'detail': _answer_detail(entry) if entry is not None else None,
                })
            domains_detail.append({'key': key, 'label': label, 'items': items})
    else:
        for qkey, value in answers.items():
            detail = _answer_detail(value)
            generic_answers.append({
                'key': qkey,
                'value': detail['value'],
                'value_label': detail['value_label'],
                'timed_out': detail['timed_out'],
            })

    return {
        'has_domain_answers': has_domain_answers,
        'domain_scores': domain_scores,
        'quality': quality,
        'domains_detail': domains_detail,
        'generic_answers': generic_answers,
    }


@admin.register(Survey)
class SurveyAdmin(AdminTitleMixin, admin.ModelAdmin):
    changelist_title = '변경할 설문 선택'
    list_display = ('id', 'title', 'created_at')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    search_fields = ('title',)
    readonly_fields = ('created_at',)
    fieldsets = (
        ('설문 정보', {'fields': ('title', 'schema')}),
        ('등록 정보', {'fields': ('created_at',)}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<path:object_id>/item-review/',
                self.admin_site.admin_view(self.item_review_view),
                name='traits_survey_item_review',
            ),
            path(
                '<path:object_id>/item-review/run/',
                self.admin_site.admin_view(self.item_review_run),
                name='traits_survey_item_review_run',
            ),
        ]
        return custom + urls

    def item_review_view(self, request, object_id):
        survey = self.get_object(request, urllib.parse.unquote(object_id))
        if survey is None:
            raise Http404
        items = survey_items(survey)
        return render(
            request,
            'admin/traits/survey/item_review.html',
            {
                **self.admin_site.each_context(request),
                'title': 'AI 문항 검토',
                'survey': survey,
                'item_count': len(items),
                'has_api_key': bool(settings.DEEPSEEK_API_KEY),
            },
        )

    def item_review_run(self, request, object_id):
        if request.method != 'POST':
            return JsonResponse({'error': 'POST 요청만 지원합니다.'}, status=405)
        survey = self.get_object(request, urllib.parse.unquote(object_id))
        if survey is None:
            return JsonResponse({'error': '설문을 찾을 수 없습니다.'}, status=404)
        if not settings.DEEPSEEK_API_KEY:
            return JsonResponse(
                {'error': 'DEEPSEEK_API_KEY 환경변수(deepseek-api)가 설정되지 않았습니다.'},
                status=503,
            )
        prompt = build_item_review_prompt(survey_items(survey))

        def generate():
            try:
                resp = requests.post(
                    DEEPSEEK_API_URL,
                    headers={
                        'Authorization': f'Bearer {settings.DEEPSEEK_API_KEY}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': DEEPSEEK_MODEL,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'stream': True,
                        'max_tokens': 8192,
                    },
                    timeout=(10, 300),
                    stream=True,
                )
                resp.raise_for_status()
            except requests.RequestException as exc:
                logger.warning('DeepSeek item review failed: %s', exc)
                yield f'\n\n[오류] DeepSeek API 호출에 실패했습니다: {exc}'
                return
            try:
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith('data:'):
                        continue
                    data = line[len('data:'):].strip()
                    if data == '[DONE]':
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    try:
                        delta = chunk['choices'][0]['delta'].get('content') or ''
                    except (KeyError, IndexError, TypeError, AttributeError):
                        continue
                    if delta:
                        yield delta
            except requests.RequestException as exc:
                logger.warning('DeepSeek item review stream interrupted: %s', exc)
                yield f'\n\n[오류] 응답 스트림이 중단되었습니다: {exc}'
            finally:
                resp.close()

        return StreamingHttpResponse(generate(), content_type='text/plain; charset=utf-8')


@admin.register(SurveyResponse)
class SurveyResponseAdmin(AdminTitleMixin, admin.ModelAdmin):
    changelist_title = '변경할 설문 응답 선택'
    list_display = ('id', 'candidate', 'survey', 'respondent_email', 'created_at')
    list_filter = ('survey', 'created_at')
    search_fields = ('candidate__name', 'candidate__email', 'respondent_email')
    list_select_related = ('candidate', 'survey')
    date_hierarchy = 'created_at'
    list_per_page = 50
    readonly_fields = ('created_at',)
    fieldsets = (
        ('응시 정보', {'fields': ('candidate', 'survey', 'respondent_email', 'created_at')}),
        ('답변', {'fields': ('answers',)}),
    )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)
        if obj is not None:
            extra_context.update(_result_context(obj.answers))
        return super().change_view(request, object_id, form_url, extra_context)
