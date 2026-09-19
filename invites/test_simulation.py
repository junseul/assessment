import json
from unittest.mock import Mock, patch

import requests
from django.contrib.auth.models import User
from django.core import signing
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from games.models import GameResult
from traits.models import SurveyResponse
from traits.survey_definition import QUESTION_TEXT

from .models import Candidate
from .simulation import LENGTHS, TASKS, advance, new_run, observation, validate_action
from .simulation_llm import SimulationError, decide
from .simulation_views import SALT


class SimulationEngineTests(SimpleTestCase):
    def run_state(self, task, mode='quick'):
        return new_run('opencode-go/deepseek-v4-flash', '가상 응시자', task, mode, 42, 1)

    def test_every_protocol_completes_and_keeps_generated_timing_separate(self):
        for task in TASKS:
            with self.subTest(task=task):
                state = self.run_state(task, 'full')
                for _ in range(LENGTHS[task]):
                    public, private = observation(state)
                    if task == 'traits':
                        action = 3
                    elif task == 'expedition-investment':
                        action = 'A'
                    elif task == 'space-station-schedule':
                        action = [private['correct_action']]
                    else:
                        action = private['correct_action']
                    with patch('invites.simulation.decide', return_value={
                        'action': action, 'simulated_rt_ms': 200, 'llm_latency_ms': 2500, 'reason': '검증용 응답',
                    }):
                        row, completed = advance(state)
                    self.assertEqual(row['llm_latency_ms'], 2500)
                    self.assertEqual(row['simulated_rt_ms'], 200)
                self.assertEqual(state['task_index'], 1)
                self.assertTrue(completed['summary']['complete_protocol'])
                self.assertEqual(len(completed['records']), LENGTHS[task])
                if task == 'traits':
                    self.assertEqual(completed['summary']['response_quality']['answered'], len(QUESTION_TEXT))
                    self.assertEqual({s['score'] for s in completed['summary']['domain_scores']}, {50.0})
                elif task == 'expedition-investment':
                    amounts = [r['outcome']['amount'] for r in completed['records']]
                    self.assertTrue(set(amounts[:25]) <= {100, -150})
                    self.assertTrue(set(amounts[25:]) <= {50, 25})
                    self.assertEqual(completed['summary']['final_total'], sum(amounts))

    def test_invalid_actions_and_deadlines(self):
        for task, bad in [('traits', True), ('cipher-lab', 8), ('drone-tracking', [True, 2]),
                          ('flash-comm', ['blue']), ('space-station-schedule', ['p', 'p'])]:
            state = self.run_state(task)
            public, private = observation(state)
            self.assertFalse(validate_action(task, bad, public, private))
        state = self.run_state('traits')
        with patch('invites.simulation.decide', return_value={
            'action': 5, 'simulated_rt_ms': 60000, 'llm_latency_ms': 10, 'reason': '시간 초과',
        }):
            row, _ = advance(state)
        self.assertIsNone(row['outcome']['value'])
        self.assertTrue(row['outcome']['timed_out'])

    def test_seed_and_hidden_payoff(self):
        state = self.run_state('expedition-investment')
        self.assertEqual(observation(state), observation(self.run_state('expedition-investment')))
        with patch('invites.simulation.decide', return_value={
            'action': 'B', 'simulated_rt_ms': 700, 'llm_latency_ms': 99, 'reason': '탐색',
        }) as llm:
            advance(state)
            advance(state)
        sent = json.dumps(llm.call_args.args, ensure_ascii=False)
        for secret in ['loss_prob', 'loss_amt', 'REVERSAL', 'correct_action', 'phase']:
            self.assertNotIn(secret, sent)
        self.assertIn('feedback', sent)


class LLMTests(SimpleTestCase):
    @patch('invites.simulation_llm.credentials', return_value=('https://example.test', 'secret', 'test-model'))
    @patch('invites.simulation_llm.requests.post')
    def test_provider_validation_and_safe_errors(self, post, creds):
        response = Mock(status_code=200)
        response.json.return_value = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({
            'action': 3, 'simulated_rt_ms': 1500, 'reason': '보통',
        })}}]}
        post.return_value = response
        self.assertEqual(decide('test', 'persona', {}, [], 'run')['action'], 3)
        self.assertFalse(post.call_args.kwargs['allow_redirects'])
        self.assertNotIn('secret', json.dumps(post.call_args.kwargs['json']))
        response.status_code = 401
        response.text = 'secret provider body'
        with self.assertRaisesRegex(SimulationError, 'HTTP 401'):
            decide('test', 'persona', {}, [], 'run')
        post.side_effect = requests.Timeout('secret')
        with self.assertRaisesRegex(SimulationError, '제한시간'):
            decide('test', 'persona', {}, [], 'run')
        post.side_effect = None
        response.status_code = 200
        response.json.return_value['choices'][0]['message']['content'] = '{bad'
        with self.assertRaisesRegex(SimulationError, 'JSON'):
            decide('test', 'persona', {}, [], 'run')


@override_settings(DEBUG=True)
class SimulationPageTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('sim-admin', is_staff=True)
        self.client.force_login(self.admin)
        self.url = reverse('invites:local_test', args=['simulation'])

    def start(self, **changes):
        payload = dict(action='start', model='opencode-go/deepseek-v4-flash', profile='balanced',
                       task='traits', mode='quick', seed=42)
        payload.update(changes)
        with patch('invites.simulation_views.credentials'):
            return self.client.post(self.url, payload)

    def test_page_and_execution_do_not_touch_candidate_data_or_identity(self):
        session = self.client.session
        session['candidate_id'] = 12345
        session.save()
        self.assertContains(self.client.get(self.url), 'AI 시뮬레이션')
        started = self.start().json()
        token = started['state']
        with patch('invites.simulation.decide', return_value={
            'action': 3, 'simulated_rt_ms': 2400, 'llm_latency_ms': 110, 'reason': '<script>alert(1)</script>',
        }):
            for _ in range(5):
                response = self.client.post(self.url, {'action': 'step', 'state': token})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                token = data['state']
        self.assertTrue(data['done'])
        self.assertFalse(data['completed']['summary']['complete_protocol'])
        self.assertEqual(Candidate.objects.count(), 0)
        self.assertEqual(GameResult.objects.count(), 0)
        self.assertEqual(SurveyResponse.objects.count(), 0)
        self.assertEqual(self.client.session['candidate_id'], 12345)
        self.assertNotIn('local_test_mode', self.client.session)
        self.assertEqual(self.client.post(self.url, {'action': 'step', 'state': token}).status_code, 400)

    def test_access_csrf_and_signed_state_boundaries(self):
        anonymous = Client()
        self.assertEqual(anonymous.get(self.url).status_code, 302)
        ordinary = User.objects.create_user('ordinary')
        anonymous.force_login(ordinary)
        self.assertEqual(anonymous.get(self.url).status_code, 302)
        with override_settings(DEBUG=False):
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.assertEqual(self.client.post(self.url, {'action': 'start'}).status_code, 404)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        self.assertEqual(csrf.post(self.url, {'action': 'start'}).status_code, 403)
        self.assertEqual(self.start(seed=-1).status_code, 400)
        self.assertEqual(self.start(model='unlisted/model').status_code, 400)
        token = self.start().json()['state']
        self.assertEqual(self.client.post(self.url, {'action': 'step', 'state': token + 'x'}).status_code, 400)
        state = signing.loads(token, salt=SALT)
        state['user_id'] = ordinary.pk
        self.assertEqual(self.client.post(self.url, {'action': 'step', 'state': signing.dumps(state, salt=SALT)}).status_code, 403)
        with patch('django.core.signing.time.time', return_value=1):
            expired = signing.dumps(state, salt=SALT)
        self.assertEqual(self.client.post(self.url, {'action': 'step', 'state': expired}).status_code, 400)

    def test_llm_failure_preserves_retry_state(self):
        token = self.start().json()['state']
        with patch('invites.simulation.decide', side_effect=SimulationError('연결 실패')):
            self.assertEqual(self.client.post(self.url, {'action': 'step', 'state': token}).status_code, 502)
        with patch('invites.simulation.decide', return_value={
            'action': 2, 'simulated_rt_ms': 2300, 'llm_latency_ms': 120, 'reason': '재시도',
        }):
            retried = self.client.post(self.url, {'action': 'step', 'state': token})
        self.assertEqual(retried.json()['row']['seq'], 0)
