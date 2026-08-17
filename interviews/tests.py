from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from helpers import login_candidate

from .models import InterviewResponse


@override_settings(DEEPSEEK_API_KEY='')
class InterviewSubmitTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.url = reverse('interviews:submit_response')

    def _video(self, name='clip.webm', content=b'webm-bytes', content_type='video/webm'):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_video_required(self):
        response = self.client.post(self.url, {'transcript': '안녕하세요'})
        self.assertEqual(response.status_code, 400)

    def test_invalid_file_rejected(self):
        response = self.client.post(self.url, {
            'transcript': '안녕하세요',
            'video': self._video(name='note.txt', content=b'hello', content_type='text/plain'),
        })
        self.assertEqual(response.status_code, 400)
        self.assertFalse(InterviewResponse.objects.exists())

    def test_submit_ok(self):
        response = self.client.post(self.url, {
            'transcript': '안녕하세요',
            'video': self._video(),
        })
        self.assertEqual(response.status_code, 200)
        obj = InterviewResponse.objects.get(respondent_email=self.candidate.email)
        self.assertTrue(obj.video.name.startswith('interviews/'))
        self.assertNotEqual(obj.video.name, 'interviews/interview.webm')

    def test_duplicate_rejected(self):
        self.client.post(self.url, {'transcript': '1', 'video': self._video()})
        response = self.client.post(self.url, {'transcript': '2', 'video': self._video(name='clip2.webm')})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(InterviewResponse.objects.filter(respondent_email=self.candidate.email).count(), 1)

    def test_follow_up_requires_text_and_video(self):
        obj = InterviewResponse.objects.create(
            candidate=self.candidate,
            respondent_email=self.candidate.email,
            video=self._video(),
            follow_up_question='추가 질문',
        )
        response = self.client.post(reverse('interviews:submit_follow_up', args=[obj.pk]), {
            'transcript': '답변',
        })
        self.assertEqual(response.status_code, 400)

    def test_follow_up_submit_ok(self):
        obj = InterviewResponse.objects.create(
            candidate=self.candidate,
            respondent_email=self.candidate.email,
            video=self._video(),
            follow_up_question='추가 질문',
        )
        response = self.client.post(reverse('interviews:submit_follow_up', args=[obj.pk]), {
            'transcript': '추가 답변',
            'video': self._video(name='follow-up.webm'),
        })
        self.assertEqual(response.status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.follow_up_transcript, '추가 답변')
        self.assertIsNotNone(obj.follow_up_submitted_at)

    def test_cannot_submit_another_candidates_follow_up(self):
        other = login_candidate(self.client)
        obj = InterviewResponse.objects.create(
            candidate=self.candidate,
            respondent_email=self.candidate.email,
            video=self._video(),
            follow_up_question='추가 질문',
        )
        response = self.client.post(reverse('interviews:submit_follow_up', args=[obj.pk]), {
            'transcript': '추가 답변',
            'video': self._video(name='other.webm'),
        })
        self.assertEqual(response.status_code, 404)


class InterviewVideoServeTests(TestCase):
    def setUp(self):
        self.candidate = login_candidate(self.client)
        self.obj = InterviewResponse.objects.create(
            candidate=self.candidate,
            respondent_email=self.candidate.email,
            transcript='안녕하세요',
            video=SimpleUploadedFile('clip.webm', b'webm-bytes', content_type='video/webm'),
        )
        self.url = reverse('interviews:serve_video', args=[self.obj.pk])

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_staff_can_download(self):
        User.objects.create_user(username='hr', password='pass')
        self.client.logout()
        self.client.login(username='hr', password='pass')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

