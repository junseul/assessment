import json

from django.test import TestCase
from django.urls import reverse

from django.test import Client

from helpers import login_candidate

from .models import GameResult


class GameSubmitTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'radar-control'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'go', 'correct': True, 'rt': 300}],
            'summary': {'accuracy': 1, 'avg_rt_ms': 300, 'n_trials': 1},
        }

    def test_requires_session(self):
        response = Client().post(
            self.url,
            data=json.dumps(self.payload),
            content_type='application/json',
        )
        self.assertRedirects(response, reverse('invites:no_access'), target_status_code=403)

    def test_submit_ok(self):
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(respondent_email=self.candidate.email).exists())

    def test_unknown_slug_rejected_on_submit(self):
        response = self.client.post(
            reverse('games:submit_result', args=['not-a-real-game']),
            data=json.dumps(self.payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_slug_404s_on_play(self):
        response = self.client.get(reverse('games:play', args=['not-a-real-game']))
        self.assertEqual(response.status_code, 404)

    def test_duplicate_rejected(self):
        self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        response = self.client.post(
            self.url,
            data=json.dumps(self.payload),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(GameResult.objects.filter(respondent_email=self.candidate.email).count(), 1)

    def test_already_done_page(self):
        GameResult.objects.create(
            candidate=self.candidate,
            game_slug=self.slug,
            respondent_email=self.candidate.email,
            trials=[],
            summary={'accuracy': 1, 'avg_rt_ms': 200, 'n_trials': 1},
        )
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, '결과가 저장되었습니다')

    def test_game_accepts_browser_keyboard_events(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, 'choices: "ALL_KEYS"')
        self.assertContains(response, "compareKeys(data.response, ' ')")

    def test_play_page_is_frameable_from_same_origin(self):
        # Admin's local-test grid (games.views.admin_grid) embeds this page
        # in an iframe; Django's default X-Frame-Options: DENY would silently
        # block it.
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertEqual(response.headers.get('X-Frame-Options'), 'SAMEORIGIN')

    def test_index_lists_all_nine_games_as_playable(self):
        response = self.client.get(reverse('games:index'))
        self.assertEqual(response.status_code, 200)
        for title in [
            '레이더 관제', '긴급 제동', '물류 분류센터', '우주기지 일정관리', '드론 추적',
            '품질검사관', '암호 연구소', '순간 통신', '탐사대 투자',
        ]:
            self.assertContains(response, title)
        self.assertNotContains(response, '준비중')
        self.assertContains(response, '시작하기', count=9)

    def test_same_email_candidates_are_isolated(self):
        self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        other = login_candidate(self.client, candidate=type(self.candidate).objects.create(
            name='동명이메일', birthdate=self.candidate.birthdate,
            phone='010-9999-9999', email=self.candidate.email,
        ))
        response = self.client.post(
            self.url, data=json.dumps(self.payload), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=other).exists())


class EmergencyBrakeTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'emergency-brake'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'go', 'correct': True, 'rt': 300, 'ssd_ms': None}],
            'summary': {'mean_go_rt_ms': 300, 'ssrt_ms': 210, 'stop_success_rate': 0.5},
        }

    def test_game_renders_stop_signal_staircase(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, 'choices: "ALL_KEYS"')
        self.assertContains(response, 'stop-armed')
        self.assertContains(response, 'SSD_STEP_MS')

    def test_submit_ok(self):
        response = self.client.post(
            self.url, data=json.dumps(self.payload), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())

    def test_already_done_page(self):
        GameResult.objects.create(
            candidate=self.candidate,
            game_slug=self.slug,
            respondent_email=self.candidate.email,
            trials=[],
            summary={'ssrt_ms': 200},
        )
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, '결과가 저장되었습니다')


class SortingCenterTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'sorting-center'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'sort', 'rule': 'color', 'is_switch': False, 'correct': True, 'rt': 500}],
            'summary': {'switch_cost_ms': 120, 'perseverative_error_count': 1},
        }

    def test_game_renders_rule_cue(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, '색상 기준')
        self.assertContains(response, 'is_perseverative_error')

    def test_submit_ok(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())


class QualityInspectorTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'quality-inspector'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'search', 'set_size': 20, 'has_target': True, 'correct': True, 'rt': 900}],
            'summary': {'search_slope_ms_per_item': 12.5},
        }

    def test_game_renders_search_grid(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, "choices: ['f', 'j']")
        self.assertContains(response, 'search-grid')

    def test_submit_ok(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())


class DroneTrackingTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'drone-tracking'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'mot', 'n_targets': 2, 'tracking_accuracy': 1, 'fully_correct': True}],
            'summary': {'tracking_accuracy': 1, 'tracking_capacity': 2},
        }

    def test_game_renders_arena(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, 'motArena')
        self.assertContains(response, 'target-highlight')

    def test_submit_ok(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())


class CipherLabTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'cipher-lab'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'cipher', 'tier': 1, 'correct': True, 'rt': 2000}],
            'summary': {'complexity_threshold': 2},
        }

    def test_game_renders_option_grid(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, "choices: ['1', '2', '3', '4']")
        self.assertContains(response, 'cipher-panel')

    def test_submit_ok(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())


class SpaceStationScheduleTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'space-station-schedule'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'ongoing', 'correct': True, 'rt': 700}],
            'summary': {'overall_pm_accuracy': 0.75, 'clock_check_count': 3},
        }

    def test_game_renders_dual_task(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, '시간 확인')
        self.assertContains(response, 'EVENT_CUE_INDICES')

    def test_submit_ok(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())


class FlashCommTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'flash-comm'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'lag': 2, 't1_correct': True, 't2_correct': False}],
            'summary': {'t2_given_t1_accuracy': 0.4, 'accuracy_by_lag': {'2': 0.4}},
        }

    def test_game_renders_rsvp_stream(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, 'rsvp-item')
        self.assertContains(response, "choices: ['파란색', '주황색']")

    def test_submit_ok(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())


class ExpeditionInvestmentTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.slug = 'expedition-investment'
        self.url = reverse('games:submit_result', args=[self.slug])
        self.payload = {
            'trials': [{'trial_stage': 'choice', 'deck': 'C', 'amount': 50, 'is_loss': False, 'phase': 'pre'}],
            'summary': {'learning_rate': 0.02, 'reversal_adaptation': 0.1},
        }

    def test_game_renders_deck_choices(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, "'A 지역', 'B 지역', 'C 지역', 'D 지역'")
        self.assertContains(response, 'REVERSAL_INDEX')

    def test_game_computes_risk_attitude_metrics(self):
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertContains(response, 'outcome_variance')
        self.assertContains(response, 'loss_chasing_index')

    def test_submit_ok(self):
        response = self.client.post(self.url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(GameResult.objects.filter(candidate=self.candidate, game_slug=self.slug).exists())

    def test_deck_payoffs_not_exposed_in_page_source(self):
        # The payoff table used to be inlined as JS literals (decks = {A: {winAmt: ...}}),
        # letting anyone read exact win/loss odds from devtools instead of playing under
        # genuine uncertainty. It must now live server-side only (see games.views.EXPEDITION_BASE_DECKS).
        response = self.client.get(reverse('games:play', args=[self.slug]))
        self.assertNotContains(response, 'winAmt')
        self.assertNotContains(response, 'lossProb')
        self.assertNotContains(response, 'lossAmt')

    def test_round_endpoint_resolves_choice(self):
        response = self.client.post(
            reverse('games:expedition_round'),
            data=json.dumps({'deck': 'A'}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['deck'], 'A')
        self.assertIn('amount', body)
        self.assertIn(body['is_loss'], [True, False])
        self.assertEqual(body['trial_index'], 0)
        self.assertEqual(body['phase'], 'pre')

    def test_round_endpoint_rejects_invalid_deck(self):
        response = self.client.post(
            reverse('games:expedition_round'),
            data=json.dumps({'deck': 'Z'}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_round_endpoint_flips_to_post_phase_after_reversal_index(self):
        round_url = reverse('games:expedition_round')
        for _ in range(50):
            self.client.post(round_url, data=json.dumps({'deck': 'A'}), content_type='application/json')
        response = self.client.post(round_url, data=json.dumps({'deck': 'A'}), content_type='application/json')
        self.assertEqual(response.json()['phase'], 'post')

    def test_round_endpoint_blocks_after_100_rounds(self):
        round_url = reverse('games:expedition_round')
        for _ in range(100):
            self.client.post(round_url, data=json.dumps({'deck': 'A'}), content_type='application/json')
        response = self.client.post(round_url, data=json.dumps({'deck': 'A'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_round_endpoint_requires_session(self):
        response = Client().post(
            reverse('games:expedition_round'),
            data=json.dumps({'deck': 'A'}), content_type='application/json',
        )
        self.assertRedirects(response, reverse('invites:no_access'), target_status_code=403)
