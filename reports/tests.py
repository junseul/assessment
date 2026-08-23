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
        # 결과 분석 카테고리 + 지원자 리포트 링크 (전체 결과 조회)
        self.assertContains(response, '결과 분석')
        self.assertContains(response, '지원자 리포트')
        self.assertContains(response, reverse('reports:candidate_list'))
        # 우측 상단 유저링크에서 '지원자 목록' 링크가 제거되어야 한다.
        self.assertNotContains(response, '>지원자 목록</a>')
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

    def test_sidebar_menu_order(self):
        import re
        response = self.client.get('/admin/')
        body = response.content.decode('utf-8')
        m = re.search(r'<nav[^>]*id="nav-sidebar".*?</nav>', body, re.S)
        self.assertIsNotNone(m)
        side = m.group(0)

        anchors = [
            '/admin/auth/" class="section"',
            '/admin/invites/" class="section"',
            '/admin/traits/" class="section"',
            '/admin/games/" class="section"',
            '/admin/interviews/" class="section"',
            '결과 분석',
            'local-test-menu',
        ]
        positions = [side.find(a) for a in anchors]
        for anchor, pos in zip(anchors, positions):
            self.assertGreaterEqual(pos, 0, f'{anchor} 이(가) 사이드바에 없습니다')
        self.assertEqual(positions, sorted(positions), f'메뉴 순서가 잘못되었습니다: {positions}')

    def test_changelist_titles_use_korean_model_names(self):
        cases = [
            ('/admin/invites/candidate/', '변경할 지원자 선택'),
            ('/admin/invites/invite/', '변경할 초대 링크 선택'),
            ('/admin/traits/survey/', '변경할 설문 선택'),
            ('/admin/traits/surveyresponse/', '변경할 설문 응답 선택'),
            ('/admin/games/gameresult/', '변경할 게임 결과 선택'),
            ('/admin/interviews/interviewresponse/', '변경할 면접 응답 선택'),
        ]
        for url, title in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, f'<h1>{title}</h1>')


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
        self.assertContains(response, '<label>최종 자원:</label>')
        self.assertContains(response, '<div class="readonly">0</div>', count=1)
        self.assertContains(response, '<div class="readonly">0.0</div>', count=2)
        # setUp's plain go-nogo result must still use the generic accuracy block.
        self.assertContains(response, '정확한 반응 억제')

    def test_zero_survey_score_renders_as_zero_not_dash(self):
        survey = Survey.objects.create(title='역량 설문', schema={})
        SurveyResponse.objects.create(
            candidate=self.candidate, survey=survey, respondent_email=self.candidate.email,
            answers={'q001': 1},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '0.0 / 100')

    def test_radar_metrics_render(self):
        GameResult.objects.create(
            candidate=self.candidate, game_slug='radar-control',
            respondent_email=self.candidate.email, trials=[],
            summary={'accuracy': 0.85, 'mean_rt_ms': 320, 'n_trials': 70},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '<label>정확도:</label>')
        self.assertContains(response, '<div class="readonly">0.85</div>')
        self.assertContains(response, '<div class="readonly">320</div>')
        self.assertContains(response, '<div class="readonly">70</div>')
        self.assertContains(response, '대체로 안정적')
        # 완료 현황: 9개 게임 각각의 상태 — 완료한 게임만 '완료', 나머지는 '미완료'
        self.assertContains(response, '<label>전략게임 · 레이더 관제:</label>')
        self.assertContains(response, '<label>전략게임 · 긴급 제동:</label>')
        self.assertContains(response, '<div class="readonly">미완료</div>')

    def test_emergency_brake_metrics_render(self):
        GameResult.objects.create(
            candidate=self.candidate, game_slug='emergency-brake',
            respondent_email=self.candidate.email, trials=[],
            summary={'mean_go_rt_ms': 280, 'stop_success_rate': 0.9, 'n_trials': 70},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '<label>GO 평균 반응시간(ms):</label>')
        self.assertContains(response, '<div class="readonly">280</div>')
        self.assertContains(response, '<div class="readonly">0.9</div>')
        self.assertContains(response, '<div class="readonly">70</div>')
        self.assertContains(response, '억제 성공률 높음')

    def test_space_station_metrics_render_with_trial_count(self):
        trials = [
            {'trial_stage': 'ongoing'},
            {'trial_stage': 'ongoing'},
            {'trial_stage': 'event_pm'},
        ]
        GameResult.objects.create(
            candidate=self.candidate, game_slug='space-station-schedule',
            respondent_email=self.candidate.email, trials=trials,
            summary={'ongoing_accuracy': 0.8, 'ongoing_mean_rt_ms': 410},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '<label>점검 정확도:</label>')
        self.assertContains(response, '<div class="readonly">0.8</div>')
        self.assertContains(response, '<div class="readonly">410</div>')
        self.assertContains(response, '<div class="readonly">2</div>')
        self.assertContains(response, '점검 정확도 보통')

    def test_flash_comm_metrics_render(self):
        GameResult.objects.create(
            candidate=self.candidate, game_slug='flash-comm',
            respondent_email=self.candidate.email, trials=[],
            summary={'t1_accuracy': 0.8, 't2_accuracy': 0.6, 'n_sequences': 24},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        self.assertContains(response, '<label>첫 번째 신호 정확도:</label>')
        self.assertContains(response, '<div class="readonly">0.8</div>')
        self.assertContains(response, '<div class="readonly">24</div>')
        self.assertContains(response, '신호 회상 정확도 보통')

    def test_zero_metric_renders_as_zero_not_dash(self):
        GameResult.objects.create(
            candidate=self.candidate, game_slug='radar-control',
            respondent_email=self.candidate.email, trials=[],
            summary={
                'accuracy': 0, 'mean_rt_ms': 0, 'rt_sd_ms': 0,
                'omission_error_rate': 0, 'commission_error_rate': 0, 'n_trials': 0,
            },
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        # 레이더 지표 6개가 모두 0으로 채워져 있으므로 6건 모두 '0'으로 렌더링된다
        self.assertContains(response, '<div class="readonly">0</div>', count=6)
        self.assertNotContains(response, '<div class="readonly">-</div>')

    def test_missing_metric_renders_as_dash(self):
        GameResult.objects.create(
            candidate=self.candidate, game_slug='radar-control',
            respondent_email=self.candidate.email, trials=[],
            summary={'accuracy': 0.9},
        )
        self.client.login(username='hr', password='pass')
        response = self.client.get(reverse('reports:candidate_detail', args=[self.candidate.pk]))
        # 레이더 지표 6개 중 summary에 없는 5개(평균반응시간 제외 accuracy만 있음)가 '-'로 표시된다
        self.assertContains(response, '<div class="readonly">-</div>', count=5)

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

