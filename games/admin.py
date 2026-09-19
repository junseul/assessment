# -*- coding: utf-8 -*-
from django.contrib import admin

from config.admin_labels import AdminTitleMixin
from reports.views import GAME_METRICS, GENERIC_METRICS

from .models import GameResult

TRIAL_KEYS = {
    'radar-control': ['trial_stage', 'correct', 'rt'],
    'emergency-brake': ['trial_stage', 'correct', 'rt', 'ssd_ms'],
    'sorting-center': ['rule', 'is_switch', 'correct', 'rt'],
    'space-station-schedule': ['trial_stage', 'correct', 'rt'],
    'drone-tracking': ['n_targets', 'tracking_accuracy', 'fully_correct'],
    'quality-inspector': ['set_size', 'has_target', 'correct', 'rt'],
    'cipher-lab': ['tier', 'correct', 'rt'],
    'flash-comm': ['lag', 't1_correct', 't2_correct'],
    'expedition-investment': ['deck', 'amount', 'is_loss', 'phase'],
}
GENERIC_TRIAL_KEYS = ['trial_stage', 'correct', 'rt']


def _extract_trial_rows(result):
    slug = result.game_slug
    trials = result.trials
    if not isinstance(trials, list):
        return []
    keys = TRIAL_KEYS.get(slug, GENERIC_TRIAL_KEYS)
    rows = []
    for i, t in enumerate(trials[:50], 1):
        if not isinstance(t, dict):
            continue
        row = [i] + [t.get(k, '') for k in keys]
        rows.append(row)
    return rows


def _build_game_metrics(result):
    labels = GAME_METRICS.get(result.game_slug, GENERIC_METRICS)
    if result.game_slug == "space-station-schedule":
        labels = list(labels)
        labels.append(('시행 수', 'n_trials'))
    metrics = []
    for label, key in labels:
        value = result.summary.get(key) if isinstance(result.summary, dict) else None
        if result.game_slug == 'space-station-schedule' and key == 'n_trials' and value is None:
            value = len([t for t in (result.trials or []) if isinstance(t, dict) and t.get('trial_stage') == 'ongoing']) or None
        metrics.append((label, None if value is None else str(value)))
    return metrics


@admin.register(GameResult)
class GameResultAdmin(AdminTitleMixin, admin.ModelAdmin):
    changelist_title = '변경할 게임 결과 선택'
    list_display = ('id', 'candidate', 'game_slug', 'respondent_email', 'created_at')
    list_display_links = ('id', 'candidate')
    list_filter = ('game_slug', 'created_at')
    search_fields = ('candidate__name', 'candidate__email', 'respondent_email')
    list_select_related = ('candidate',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    readonly_fields = ('candidate', 'game_slug', 'respondent_email', 'created_at')
    fieldsets = (
        ('응시 정보', {'fields': ('candidate', 'game_slug', 'respondent_email', 'created_at')}),
    )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            try:
                result = GameResult.objects.get(pk=object_id)
                extra_context['game_metrics'] = _build_game_metrics(result)
                extra_context['trial_count'] = len(result.trials) if isinstance(result.trials, list) else 0
                extra_context['trial_columns'] = TRIAL_KEYS.get(result.game_slug, GENERIC_TRIAL_KEYS)
                extra_context['trial_rows'] = _extract_trial_rows(result)
            except GameResult.DoesNotExist:
                pass
        return super().changeform_view(request, object_id, form_url, extra_context)
