from django.contrib import admin

from .models import GameResult


@admin.register(GameResult)
class GameResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate', 'game_slug', 'respondent_email', 'created_at')
    list_filter = ('game_slug', 'created_at')
    search_fields = ('candidate__name', 'candidate__email', 'respondent_email')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('응시 정보', {'fields': ('candidate', 'game_slug', 'respondent_email', 'created_at')}),
        ('결과 요약', {'fields': ('summary',)}),
        ('시행 데이터', {'fields': ('trials',), 'classes': ('collapse',)}),
    )
