from django.db import models


class GameResult(models.Model):
    """One completed play-through of a jsPsych cognitive task."""
    candidate = models.ForeignKey(
        'invites.Candidate', on_delete=models.CASCADE, related_name='game_results',
        null=True, blank=True,
    )
    game_slug = models.SlugField(default='go-nogo')
    respondent_email = models.EmailField()
    trials = models.JSONField()   # raw per-trial jsPsych data
    summary = models.JSONField()  # {accuracy, avg_rt_ms, ...}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.respondent_email} - {self.game_slug}'
