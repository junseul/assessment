import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from games.catalog import GAMES
from games.models import GameResult
from traits.models import Survey
from helpers import login_candidate, make_candidate

from .models import Candidate, Invite


class VerifyTests(TestCase):
    def setUp(self):
        self.candidate = make_candidate()
        self.invite = Invite.objects.create(candidate=self.candidate)
        self.url = reverse('invites:verify', args=[self.invite.token])

    def test_wrong_identity_rejected(self):
        response = self.client.post(self.url, {
            'name': '임꺽정',
            'birthdate': '1990-01-15',
            'phone': '010-1234-5678',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '일치하지 않습니다')
        self.assertIsNone(self.client.session.get('candidate_id'))

    def test_phone_digits_match(self):
        response = self.client.post(self.url, {
            'name': '홍길동',
            'birthdate': '1990-01-15',
            'phone': '01012345678',
        })
        self.assertRedirects(response, reverse('invites:start'), fetch_redirect_response=False)
        self.assertEqual(self.client.session['candidate_email'], self.candidate.email)
        self.invite.refresh_from_db()
        self.assertIsNotNone(self.invite.used_at)

    def test_reverify_keeps_first_used_at(self):
        first_used = timezone.now() - timedelta(hours=2)
        self.invite.used_at = first_used
        self.invite.save(update_fields=['used_at'])

        self.client.post(self.url, {
            'name': '홍길동',
            'birthdate': '1990-01-15',
            'phone': '010-1234-5678',
        })
        self.invite.refresh_from_db()
        self.assertEqual(self.invite.used_at, first_used)


class StartTests(TestCase):
    def test_requires_session(self):
        response = self.client.get(reverse('invites:start'))
        self.assertRedirects(response, reverse('invites:no_access'), target_status_code=403)

    def test_uses_first_existing_survey(self):
        Survey.objects.all().delete()
        Survey.objects.create(title='old', schema={'title': 'old'})
        keep = Survey.objects.create(title='keep', schema={'title': 'keep'})
        Survey.objects.filter(title='old').delete()
        login_candidate(self.client)
        response = self.client.get(reverse('invites:start'))
        self.assertRedirects(
            response,
            reverse('traits:survey_detail', args=[keep.pk]),
            fetch_redirect_response=False,
        )

    def test_start_routes_to_first_game_before_survey_done(self):
        Survey.objects.all().delete()
        candidate = login_candidate(self.client)
        response = self.client.get(reverse('invites:start'))
        self.assertRedirects(
            response, reverse('games:index'), fetch_redirect_response=False,
        )

        # 게임을 하나도 못 끝냈으면 다음 게임(1번)로 진행된다.
        response = self.client.get(reverse('games:index'))
        self.assertRedirects(
            response, reverse('games:play', args=['radar-control']), fetch_redirect_response=False,
        )

    def test_start_moves_to_interview_after_all_games_done(self):
        Survey.objects.all().delete()
        candidate = login_candidate(self.client)
        for game in GAMES:
            if game['implemented']:
                GameResult.objects.create(
                    candidate=candidate, game_slug=game['slug'],
                    respondent_email=candidate.email, trials=[], summary={},
                )
        response = self.client.get(reverse('invites:start'))
        self.assertRedirects(
            response,
            reverse('interviews:interview_detail'),
            fetch_redirect_response=False,
        )


@override_settings(DEBUG=True)
class LocalTestTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.candidate = make_candidate()
        self.client.force_login(self.admin)

    def test_game_link_renders_admin_grid_iframe_with_sidebar(self):
        response = self.client.get(reverse('invites:local_test', args=['games']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="nav-sidebar"')
        self.assertContains(response, reverse('games:admin_grid'))
        # 로컬 테스트는 접속자(관리자) 본인 명의의 전용 후보로 진행된다.
        session_candidate = Candidate.objects.get(pk=self.client.session['candidate_id'])
        self.assertEqual(session_candidate.name, 'admin')
        self.assertEqual(session_candidate.email, 'local-test-admin@example.com')
        # 로컬 테스트 페이지에 접속자 식별과 결과 보기 링크가 노출된다.
        self.assertContains(response, 'local-test-admin@example.com')
        self.assertContains(response, reverse('reports:candidate_detail', args=[session_candidate.pk]))
        # 같은 관리자가 다시 접속해도 같은 후보가 재사용된다.
        self.client.get(reverse('invites:local_test', args=['games']))
        self.assertEqual(Candidate.objects.filter(email='local-test-admin@example.com').count(), 1)

    def test_traits_and_interviews_links_also_render_admin_iframe(self):
        response = self.client.get(reverse('invites:local_test', args=['interviews']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="nav-sidebar"')
        self.assertContains(response, reverse('interviews:interview_detail'))

    def test_admin_grid_lists_all_nine_games_as_playable(self):
        self.client.get(reverse('invites:local_test', args=['games']))
        response = self.client.get(reverse('games:admin_grid'))
        self.assertEqual(response.status_code, 200)
        for title in ['레이더 관제', '긴급 제동', '탐사대 투자']:
            self.assertContains(response, title)
        self.assertContains(response, reverse('games:play', args=['radar-control']))
        self.assertContains(response, 'class="game-select-card"', count=9)
        # Django's default X-Frame-Options: DENY would silently block this
        # page inside the admin_local_test.html iframe.
        self.assertEqual(response.headers.get('X-Frame-Options'), 'SAMEORIGIN')

    def test_local_game_submission_saves_new_result_per_attempt(self):
        self.client.get(reverse('invites:local_test', args=['games']))
        candidate = Candidate.objects.get(pk=self.client.session['candidate_id'])
        payload = json.dumps({'trials': [{'t': 1}], 'summary': {'accuracy': 1}})
        for _ in range(2):
            response = self.client.post(
                reverse('games:submit_result', args=['radar-control']),
                data=payload,
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['local_test'])
        results = list(GameResult.objects.filter(candidate=candidate).order_by('id'))
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].respondent_email, 'local-test-admin@example.com')
        self.assertEqual(results[1].summary, {'accuracy': 1})

    @override_settings(DEBUG=False)
    def test_local_test_is_disabled_outside_debug(self):
        response = self.client.get(reverse('invites:local_test', args=['games']))
        self.assertEqual(response.status_code, 404)

