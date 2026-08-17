import json

from django.test import TestCase
from django.urls import reverse

from helpers import login_candidate

from .models import Survey, SurveyResponse
from .survey_definition import score_answers


class SurveySubmitTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.survey = Survey.objects.create(
            title='성향파악',
            schema={'title': '성향파악', 'pages': []},
        )
        self.url = reverse('traits:submit_response', args=[self.survey.pk])
        self.answers = {f'q{number:03d}': 3 for number in range(1, 171)}

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


class SurveyScoringTests(TestCase):
    def test_reverse_item_is_scored_in_opposite_direction(self):
        domains = score_answers({'q007': 1})
        self.assertEqual(domains[0]['average'], 5)
        self.assertEqual(domains[0]['score'], 100)

