from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
import hashlib

class Secret(models.Model):
    SECRET_STATUS_CHOICES = [
        ('new', 'New'),
        ('triaged', 'Triaged'),
        ('false_positive', 'False Positive'),
    ]

    CRITICALITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    secret = models.TextField()
    secret_hash = models.CharField(max_length=64, editable=False)  # SHA256 hash
    source = models.CharField(max_length=255)
    kind = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=SECRET_STATUS_CHOICES, default='new')
    locations = models.JSONField()  # Store as JSON: [{"repo": "repo1", "file": "file1"}, ...]
    sources = models.JSONField()  # Store as JSON if multiple sources
    environment = models.CharField(max_length=255)
    criticality = models.CharField(max_length=20, choices=CRITICALITY_CHOICES, default='low')
    short_notes = models.TextField(blank=True)
    team = models.CharField(max_length=255)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    version = models.IntegerField(default=1)

    class Meta:
        unique_together = ('secret_hash', 'source', 'locations')

    def __str__(self):
        return f"{self.kind} secret in {self.source}"

    def save(self, *args, **kwargs):
        if not self.secret_hash:
            self.secret_hash = hashlib.sha256(self.secret.encode()).hexdigest()
        super().save(*args, **kwargs)

class SecretHistory(models.Model):
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE, related_name='history')
    changed_fields = models.JSONField()
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField()

    def __str__(self):
        return f"Version {self.version} of {self.secret}"