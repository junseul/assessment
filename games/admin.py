from django.contrib import admin

from config.admin_labels import AdminTitleMixin

from .models import GameResult


@admin.register(GameResult)
class GameResultAdmin(AdminTitleMixin, admin.ModelAdmin):
    changelist_title = '변경할 게임 결과 선택'
    list_display = ('id', 'candidate', 'game_slug', 'respondent_email', 'created_at')
    list_filter = ('game_slug', 'created_at')
    search_fields = ('candidate__name', 'candidate__email', 'respondent_email')
    list_select_related = ('candidate',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    readonly_fields = ('created_at',)
    fieldsets = (
        ('응시 정보', {'fields': ('candidate', 'game_slug', 'respondent_email', 'created_at')}),
        ('결과 요약', {'fields': ('summary',)}),
        ('시행 데이터', {'fields': ('trials',), 'classes': ('collapse',)}),
    )
