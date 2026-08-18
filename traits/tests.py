import json

from django.test import TestCase
from django.urls import reverse

from helpers import login_candidate

from .models import Survey, SurveyResponse
from .survey_definition import QUESTION_TEXT, response_quality, score_answers


class SurveySubmitTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.survey = Survey.objects.create(
            title='성향파악',
            schema={'title': '성향파악', 'pages': []},
        )
        self.url = reverse('traits:submit_response', args=[self.survey.pk])
        self.answers = {
            f'q{number:03d}': {'value': 3, 'rt_ms': 2000, 'timed_out': False}
            for number in range(1, 171)
        }

    def test_page_uses_json_script(self):
        response = self.client.get(reverse('traits:survey_detail', args=[self.survey.pk]))
        self.assertContains(response, 'id="survey-schema"')
        self.assertContains(response, 'id="timeBar"')
        self.assertContains(response, 'remaining / currentLimitMs * 100')
        self.assertNotContains(response, 'const schema = {')

    def test_page_is_frameable_from_same_origin(self):
        # Admin's local-test iframe (invites.views.local_test) embeds this
        # page; Django's default X-Frame-Options: DENY would silently block it.
        response = self.client.get(reverse('traits:survey_detail', args=[self.survey.pk]))
        self.assertEqual(response.headers.get('X-Frame-Options'), 'SAMEORIGIN')

    def test_submit_ok(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'answers': self.answers}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            SurveyResponse.objects.filter(
                survey=self.survey,
                respondent_email=self.candidate.email,
            ).exists()
        )

    def test_duplicate_rejected(self):
        body = json.dumps({'answers': self.answers})
        self.client.post(self.url, data=body, content_type='application/json')
        response = self.client.post(self.url, data=body, content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            SurveyResponse.objects.filter(
                survey=self.survey,
                respondent_email=self.candidate.email,
            ).count(),
            1,
        )

    def test_invalid_or_incomplete_answers_rejected(self):
        response = self.client.post(
            self.url,
            data=json.dumps({'answers': {'q001': 6}}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_timed_out_answer_with_null_value_accepted(self):
        answers = dict(self.answers)
        answers['q001'] = {'value': None, 'rt_ms': 8000, 'timed_out': True}
        response = self.client.post(
            self.url, data=json.dumps({'answers': answers}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_negative_rt_ms_rejected(self):
        answers = dict(self.answers)
        answers['q001'] = {'value': 3, 'rt_ms': -1, 'timed_out': False}
        response = self.client.post(
            self.url, data=json.dumps({'answers': answers}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_timed_out_flag_inconsistent_with_value_rejected(self):
        answers = dict(self.answers)
        answers['q001'] = {'value': 3, 'rt_ms': 2000, 'timed_out': True}
        response = self.client.post(
            self.url, data=json.dumps({'answers': answers}), content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)


class SurveyScoringTests(TestCase):
    def test_reverse_item_is_scored_in_opposite_direction(self):
        # Bare-number shape: how older SurveyResponse rows already stored in
        # the DB looked before response-time tracking was added.
        domains = score_answers({'q007': 1})
        self.assertEqual(domains[0]['average'], 5)
        self.assertEqual(domains[0]['score'], 100)

    def test_current_shape_scores_the_same_as_bare_number(self):
        domains = score_answers({'q007': {'value': 1, 'rt_ms': 3000, 'timed_out': False}})
        self.assertEqual(domains[0]['average'], 5)
        self.assertEqual(domains[0]['score'], 100)

    def test_timed_out_answers_are_counted_and_excluded_from_average(self):
        domains = score_answers({
            'q001': {'value': None, 'rt_ms': 8000, 'timed_out': True},
            'q002': {'value': 4, 'rt_ms': 2000, 'timed_out': False},
        })
        self.assertEqual(domains[0]['timed_out'], 1)
        self.assertEqual(domains[0]['answered'], 1)
        self.assertEqual(domains[0]['average'], 4)


class ResponseQualityTests(TestCase):
    """Simulated response patterns per the improvement directive's section 9:
    all-max, all-min, mid-only, random, and abnormally-fast responding."""

    def make_answers(self, value_for, rt_for=lambda n: 3000):
        return {
            f'q{n:03d}': {'value': value_for(n), 'rt_ms': rt_for(n), 'timed_out': value_for(n) is None}
            for n in range(1, len(QUESTION_TEXT) + 1)
        }

    def test_all_max_answers_are_fully_extreme(self):
        quality = response_quality(self.make_answers(lambda n: 5))
        self.assertEqual(quality['answered'], len(QUESTION_TEXT))
        self.assertEqual(quality['extreme_response_rate'], 1.0)

    def test_all_min_answers_are_fully_extreme(self):
        quality = response_quality(self.make_answers(lambda n: 1))
        self.assertEqual(quality['extreme_response_rate'], 1.0)

    def test_all_midpoint_answers_have_zero_extreme_rate(self):
        quality = response_quality(self.make_answers(lambda n: 3))
        self.assertEqual(quality['extreme_response_rate'], 0.0)

    def test_random_answers_extreme_rate_within_bounds(self):
        import random
        rng = random.Random(42)
        quality = response_quality(self.make_answers(lambda n: rng.randint(1, 5)))
        self.assertIsNotNone(quality['extreme_response_rate'])
        self.assertGreaterEqual(quality['extreme_response_rate'], 0.0)
        self.assertLessEqual(quality['extreme_response_rate'], 1.0)

    def test_abnormally_fast_responses_are_flagged(self):
        quality = response_quality(self.make_answers(lambda n: 3, rt_for=lambda n: 200))
        self.assertEqual(quality['fast_response_rate'], 1.0)
        self.assertEqual(quality['avg_rt_ms'], 200)

    def test_normal_pace_responses_are_not_flagged_as_fast(self):
        quality = response_quality(self.make_answers(lambda n: 3, rt_for=lambda n: 4000))
        self.assertEqual(quality['fast_response_rate'], 0.0)

    def test_empty_answers_return_none_rates_not_errors(self):
        quality = response_quality({})
        self.assertEqual(quality['answered'], 0)
        self.assertIsNone(quality['extreme_response_rate'])
        self.assertIsNone(quality['avg_rt_ms'])
        self.assertIsNone(quality['fast_response_rate'])

