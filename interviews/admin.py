from django.contrib import admin

from .models import InterviewResponse


@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'candidate', 'respondent_email', 'created_at', 'follow_up_submitted_at')
    list_filter = ('created_at', 'follow_up_submitted_at')
    search_fields = ('candidate__name', 'candidate__email', 'respondent_email', 'transcript')
    readonly_fields = ('transcript', 'follow_up_question', 'created_at', 'follow_up_submitted_at')
    fieldsets = (
        ('응시 정보', {'fields': ('candidate', 'respondent_email', 'created_at')}),
        ('1차 답변', {'fields': ('question', 'transcript', 'video')}),
        ('후속 답변', {'fields': (
            'follow_up_question', 'follow_up_transcript', 'follow_up_video',
            'follow_up_submitted_at',
        )}),
    )
