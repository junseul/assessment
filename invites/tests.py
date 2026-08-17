import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from games.models import GameResult
from traits.models import Survey
from helpers import login_candidate, make_candidate

from .models import Invite


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


@override_settings(DEBUG=True)
class LocalTestTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pass')
        self.candidate = make_candidate()
        self.client.force_login(self.admin)

    def test_game_link_sets_candidate_session(self):
        response = self.client.get(reverse('invites:local_test', args=['games']))
        self.assertRedirects(response, reverse('games:go_nogo'), fetch_redirect_response=False)
        self.assertEqual(self.client.session['candidate_id'], self.candidate.pk)

    def test_local_game_submission_does_not_write_result(self):
        self.client.get(reverse('invites:local_test', args=['games']))
        response = self.client.post(
            reverse('games:submit_result'),
            data=json.dumps({'trials': [], 'summary': {}}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['local_test'])
        self.assertFalse(GameResult.objects.exists())

    @override_settings(DEBUG=False)
    def test_local_test_is_disabled_outside_debug(self):
        response = self.client.get(reverse('invites:local_test', args=['games']))
        self.assertEqual(response.status_code, 404)

