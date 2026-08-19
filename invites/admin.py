from django.conf import settings
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .models import Candidate, Invite


def invite_url(invite):
    return settings.SITE_BASE_URL + reverse('invites:verify', args=[invite.token])


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'birthdate', 'created_at', 'report_link')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    readonly_fields = ('created_at',)
    fieldsets = (
        ('기본 정보', {'fields': ('name', 'birthdate')}),
        ('연락처', {'fields': ('phone', 'email')}),
        ('등록 정보', {'fields': ('created_at',)}),
    )
    actions = ['create_invite_link']

    @admin.display(description='리포트')
    def report_link(self, obj):
        return format_html('<a href="{}">보기</a>', reverse('reports:candidate_detail', args=[obj.pk]))

    @admin.action(description='초대 링크 생성 (1회용)')
    def create_invite_link(self, request, queryset):
        for candidate in queryset:
            invite = Invite.objects.create(candidate=candidate)
            self.message_user(request, f'{candidate.name}: {invite_url(invite)}', level=messages.SUCCESS)


@admin.register(Invite)
class InviteAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'status', 'full_link', 'created_at', 'used_at')
    list_filter = ('used_at', 'created_at')
    search_fields = ('candidate__name', 'candidate__email', 'token')
    list_select_related = ('candidate',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    readonly_fields = ('token', 'full_link', 'created_at', 'used_at')
    fieldsets = (
        ('응시자', {'fields': ('candidate',)}),
        ('초대 링크', {'fields': ('full_link', 'token')}),
        ('사용 기록', {'fields': ('created_at', 'used_at')}),
    )

    @admin.display(description='초대 링크')
    def full_link(self, obj):
        url = invite_url(obj)
        return format_html('<a href="{0}" target="_blank">{0}</a>', url)

    @admin.display(description='상태', ordering='used_at')
    def status(self, obj):
        label = '사용 완료' if obj.used_at else '미사용'
        state = 'complete' if obj.used_at else 'pending'
        return format_html('<span class="status-badge status-{}">{}</span>', state, label)
