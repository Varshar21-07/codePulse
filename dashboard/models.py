from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    github_username = models.CharField(max_length=100, blank=True, null=True)
    access_token = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username

class Stats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stats')
    repo_name = models.CharField(max_length=255, blank=True, null=True)
    total_prs = models.IntegerField(default=0)
    merged_prs = models.IntegerField(default=0)
    open_prs = models.IntegerField(default=0)
    closed_prs = models.IntegerField(default=0)
    total_issues = models.IntegerField(default=0)
    resolved_issues = models.IntegerField(default=0)
    productivity_score = models.FloatField(default=0.0)
    streak_days = models.IntegerField(default=0)
    last_synced = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.user.username}"
