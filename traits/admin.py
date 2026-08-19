from django.contrib import admin

from .models import Survey, SurveyResponse


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
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


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
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
