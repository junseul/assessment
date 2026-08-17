import os
import uuid

from django.db import models

DEFAULT_QUESTION = '1분 동안 자기소개를 해주세요.'


def interview_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {'.webm', '.mp4', '.ogg', '.mov'}:
        ext = '.webm'
    return f'interviews/{uuid.uuid4().hex}{ext}'


class InterviewResponse(models.Model):
    candidate = models.ForeignKey(
        'invites.Candidate', on_delete=models.CASCADE, related_name='interview_responses',
        null=True, blank=True,
    )
    respondent_email = models.EmailField()
    question = models.CharField(max_length=300, default=DEFAULT_QUESTION)
    transcript = models.TextField(blank=True)
    video = models.FileField(upload_to=interview_upload_to)
    follow_up_question = models.TextField(blank=True)
    follow_up_transcript = models.TextField(blank=True)
    follow_up_video = models.FileField(upload_to=interview_upload_to, blank=True)
    follow_up_submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.respondent_email} - {self.created_at:%Y-%m-%d}'
