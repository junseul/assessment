from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from helpers import make_candidate

from invites.models import Candidate

from .admin_views import DATE_ERROR, ORDER_ERROR, parse_query_date


class ParseQueryDateTests(TestCase):
    def test_yyyymmdd(self):
        self.assertEqual(parse_query_date('20260823'), date(2026, 8, 23))

    def test_yymmdd(self):
        self.assertEqual(parse_query_date('260823'), date(2026, 8, 23))

    def test_strips_whitespace(self):
        self.assertEqual(parse_query_date(' 20260101 '), date(2026, 1, 1))

    def test_invalid_calendar_date(self):
        with self.assertRaises(ValueError):
            parse_query_date('20261301')

    def test_invalid_length(self):
        for value in ('', '20261', '202608231', 'abc'):
            with self.assertRaises(ValueError):
                parse_query_date(value)


class DashboardIndexTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            username='admin', password='pw', is_staff=True, is_superuser=True,
        )
        cls.url = reverse('admin:index')

    def setUp(self):
        self.client.force_login(self.staff)

    def test_default_range_is_year_start_to_today(self):
        today = timezone.localdate()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '기간별 현황')
        self.assertEqual(response.context['period_start'], f'{today.year}0101')
        self.assertEqual(response.context['period_end'], today.strftime('%Y%m%d'))

    def test_query_with_yymmdd_and_counts(self):
        make_candidate()
        response = self.client.get(self.url, {'start': '260101', 'end': '261231'})
        self.assertEqual(response.status_code, 200)
        counts = {item['label']: item['count'] for item in response.context['period_results']}
        self.assertEqual(counts['지원자'], 1)

    def test_out_of_range_excluded(self):
        candidate = make_candidate()
        Candidate.objects.filter(pk=candidate.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=365 * 2),
        )
        response = self.client.get(self.url)
        counts = {item['label']: item['count'] for item in response.context['period_results']}
        self.assertEqual(counts['지원자'], 0)

    def test_invalid_format_shows_error(self):
        response = self.client.get(self.url, {'start': 'abc'})
        self.assertContains(response, DATE_ERROR)

    def test_start_after_end_shows_error(self):
        response = self.client.get(self.url, {'start': '20260823', 'end': '20260101'})
        self.assertContains(response, ORDER_ERROR)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
