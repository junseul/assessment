from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from games.models import GameResult
from helpers import make_candidate
from invites.models import Invite
from traits.models import Survey, SurveyResponse


class AdminDashboardTests(TestCase):
    def setUp(self):
        User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.client.force_login(User.objects.get(username='admin'))

    def test_index_shows_dashboard_and_sidebar_menus(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="nav-sidebar"')
        self.assertContains(response, 'id="content-main"')
        self.assertContains(response, '관리 대시보드')
        self.assertContains(response, '최근 작업')
        self.assertContains(response, 'dashboard-stats')
        self.assertContains(response, '빠른 작업')
        self.assertContains(response, 'class="app-invites module"', count=1)
        self.assertContains(response, '로컬 테스트')
        self.assertContains(response, '성향파악')
        self.assertContains(response, '전략게임')
        self.assertContains(response, '면접응답')
        self.assertContains(response, '<a href="http://127.0.0.1:8000/reports/">지원자 목록</a>', html=True)
        self.assertNotContains(response, '사이트 보기')
        self.assertContains(response, '지원자')
        self.assertContains(response, '초대 링크')
        self.assertContains(response, '설문 응답')
        self.assertContains(response, '게임 결과')
        self.assertContains(response, '면접 응답')
        self.assertContains(response, '성향파악')
        self.assertContains(response, '초대 관리')

    def test_admin_login_uses_lightdash_card(self):
        self.client.logout()
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'admin-login-card')
        self.assertContains(response, '관리자 로그인')

    def test_candidate_admin_has_search_filter_and_fieldsets(self):
        response = self.client.get('/admin/invites/candidate/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="changelist-search"')
        self.assertContains(response, 'id="changelist-filter"')

        candidate = make_candidate()
        response = self.client.get(f'/admin/invites/candidate/{candidate.pk}/change/')
        self.assertContains(response, '기본 정보')
        self.assertContains(response, '연락처')
    def test_admin_lists_have_consistent_navigation_helpers(self):
        candidate = make_candidate()
        response = self.client.get('/admin/invites/candidate/')
        self.assertContains(response, reverse('reports:candidate_detail', args=[candidate.pk]))
        self.assertContains(response, 'created_at__year')

        Invite.objects.create(candidate=candidate)
        invite_response = self.client.get('/admin/invites/invite/')
        self.assertContains(invite_response, 'status-badge')


class RootRedirectTests(TestCase):
    def test_root_redirects_to_login(self):
        response = self.client.get('/')
        self.assertRedirects(response, reverse('login'))


class ReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='hr', password='pass')
        self.candidate = make_candidate()
        GameResult.objects.create(
            candidate=self.candidate,
            respondent_email=self.candidate.email,
            trials=[],
            summary={'accuracy': 1, 'avg_rt_ms': 200, 'n_trials': 1},
        )

    def test_list_requires_login(self):
        response = self.client.get(reverse('reports:candidate_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_list_shows_candidate_name(self):
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_list'))
        self.assertContains(response, self.candidate.name)
        self.assertContains(response, self.candidate.email)

    def test_detail_requires_login(self):
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertEqual(response.status_code, 302)

    def test_detail_shows_scores_and_completion(self):
        survey = Survey.objects.create(title='역량 설문', schema={})
        SurveyResponse.objects.create(
            candidate=self.candidate,
            survey=survey,
            respondent_email=self.candidate.email,
            answers={'q001': 4},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '75.0 / 100')
        self.assertContains(response, '강점 수준')
        self.assertContains(response, '정확한 반응 억제')

    def test_expedition_investment_shows_its_own_metrics_other_games_unaffected(self):
        GameResult.objects.create(
            candidate=self.candidate,
            game_slug='expedition-investment',
            respondent_email=self.candidate.email,
            trials=[],
            summary={'final_total': 250, 'exploration_rate': 0.3, 'outcome_variance': 4200.5},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '최종 자원')
        self.assertContains(response, '결과 변동성(위험선호)')
        self.assertContains(response, '4200.5')
        # setUp's plain go-nogo result must still use the generic accuracy block.
        self.assertContains(response, '정확한 반응 억제')

    def test_zero_valued_metrics_render_as_zero_not_dash(self):
        # Django's `default` filter treats 0/0.0 as falsy and substitutes the
        # fallback, which would misreport a real "no exploration at all" or
        # "no loss chasing" result as missing data. Must use default_if_none.
        GameResult.objects.create(
            candidate=self.candidate,
            game_slug='expedition-investment',
            respondent_email=self.candidate.email,
            trials=[],
            summary={'final_total': 0, 'exploration_rate': 0.0, 'loss_chasing_index': 0.0},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '<dt>최종 자원</dt><dd>0</dd>', html=True)
        self.assertContains(response, '<dt>탐색 비율</dt><dd>0.0</dd>', html=True)
        self.assertContains(response, '<dt>손실추격 지수</dt><dd>0.0</dd>', html=True)

    def test_zero_survey_score_renders_as_zero_not_dash(self):
        survey = Survey.objects.create(title='역량 설문', schema={})
        SurveyResponse.objects.create(
            candidate=self.candidate, survey=survey, respondent_email=self.candidate.email,
            answers={'q001': 1},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '0.0 / 100')

    def test_logout_rejects_get(self):
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

    def test_logout_accepts_post(self):
        self.client.login(username='hr', password='pass')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('reports:candidate_list'))
        self.assertEqual(response.status_code, 302)

