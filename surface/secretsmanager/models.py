from django.db import models
from django.contrib.auth.models import User
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
    git_source = models.ForeignKey("inventory.GitSource", null=True, on_delete=models.SET_NULL)
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
        unique_together = ('secret_hash', 'source', 'git_source')

    def __str__(self):
        return f"{self.kind} secret in {self.source}"

    def save(self, *args, **kwargs):
        if not self.secret_hash:
            self.secret_hash = hashlib.sha256(self.secret.encode()).hexdigest()
        super().save(*args, **kwargs)

    def get_source_links(self):
        if isinstance(self.sources, dict):
            source_data = self.sources.get('SourceMetadata', {}).get('Data', {}).get('Git', {})
            if source_data:
                repo = source_data.get('repository', '')
                commit = source_data.get('commit', '')
                file = source_data.get('file', '')
                line = source_data.get('line', '')
                if all([repo, commit, file, line]):
                    # Convert repo URL if needed (e.g., remove .git suffix)
                    repo = repo.rstrip('.git')
                    return f"{repo}/blob/{commit}/{file}#L{line}"
        return None

    def get_locations(self):
        return SecretLocation.objects.filter(secret=self)

class SecretHistory(models.Model):
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE, related_name='history')
    changed_fields = models.JSONField()
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField()

    def __str__(self):
        return f"Version {self.version} of {self.secret}"

class SecretLocation(models.Model):
    secret = models.ForeignKey(Secret, on_delete=models.CASCADE, related_name='locations')
    file_path = models.CharField(max_length=255)
    commit = models.CharField(max_length=40)
    repository = models.CharField(max_length=255)
    timestamp = models.DateTimeField()
    author = models.CharField(max_length=255)
    line = models.CharField(max_length=10, default="1")

    class Meta:
        unique_together = ('secret', 'file_path', 'commit')

    def __str__(self):
        return f"{self.file_path} @ {self.commit[:8]}"

    def clean_repository_url(self):
        """Clean and standardize repository URL"""
        if self.repository:
            # Remove .git extension
            clean_url = self.repository.replace('.git', '')
            # Fix known issues
            if 'truffleho/' in clean_url:
                clean_url = clean_url.replace('truffleho/', 'trufflehog/')
            return clean_url
        return self.repository

    def save(self, *args, **kwargs):
        self.repository = self.clean_repository_url()
        super().save(*args, **kwargs)