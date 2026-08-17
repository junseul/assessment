from django.db import models


class Survey(models.Model):
    """A SurveyJS survey definition. `schema` is the raw SurveyJS JSON model."""
    title = models.CharField(max_length=200)
    schema = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class SurveyResponse(models.Model):
    candidate = models.ForeignKey(
        'invites.Candidate', on_delete=models.CASCADE, related_name='survey_responses',
        null=True, blank=True,
    )
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    respondent_email = models.EmailField()
    answers = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.respondent_email} - {self.survey.title}'
