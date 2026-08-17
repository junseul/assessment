import json

from django.test import TestCase
from django.urls import reverse

from django.test import Client

from helpers import login_candidate

from .models import GameResult


class GameSubmitTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.url = reverse('games:submit_result')
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
            respondent_email=self.candidate.email,
            trials=[],
            summary={'accuracy': 1, 'avg_rt_ms': 200, 'n_trials': 1},
        )
        response = self.client.get(reverse('games:go_nogo'))
        self.assertContains(response, '결과가 저장되었습니다')

    def test_game_accepts_browser_keyboard_events(self):
        response = self.client.get(reverse('games:go_nogo'))
        self.assertContains(response, 'choices: "ALL_KEYS"')
        self.assertContains(response, "compareKeys(data.response, ' ')")

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

