import secrets

from django.db import models


def generate_token():
    return secrets.token_urlsafe(32)


class Candidate(models.Model):
    name = models.CharField(max_length=100)
    birthdate = models.DateField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.email})'


class Invite(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='invites')
    token = models.CharField(max_length=64, unique=True, default=generate_token, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.candidate.name} - {"used" if self.used_at else "pending"}'
