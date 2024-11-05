import os
import subprocess
import tempfile
from io import StringIO
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from secretsmanager.models import Secret, SecretLocation
from inventory.models import GitSource

class ImportGitSecretsCommandTest(TestCase):
    def setUp(self):
        self.repo_path = tempfile.mkdtemp()
        self.org = "test-org"
        self.repo_url = f"https://github.com/{self.org}/test-repo"
        self.git_source = GitSource.objects.create(
            repo_url=self.repo_url,
            branch="main"
        )

    @patch('subprocess.run')
    def test_scan_git_history(self, mock_run):
        """Test scanning git history for sensitive files"""
        repo_name = os.path.basename(self.repo_path)
        expected_repo_url = f"https://github.com/{self.org}/{repo_name}"

        mock_responses = [
            MagicMock(stdout="main\n", returncode=0),  # get_default_branch
            MagicMock(stdout="commit1\n", returncode=0),  # rev-list
            MagicMock(stdout="100644 blob hash1 secret.key\n", returncode=0),  # ls-tree
            MagicMock(stdout="test@example.com\n", returncode=0),  # log (author)
            MagicMock(stdout="2024-01-01T00:00:00Z\n", returncode=0),  # log (date)
            MagicMock(stdout=b"secret content", returncode=0),  # show (file content)
            MagicMock(stdout="", returncode=0),  # ls-tree (empty result to end loop)
        ]
        mock_run.side_effect = mock_responses

        out = StringIO()
        call_command('import_git_secrets', self.repo_path, f'--org={self.org}', stdout=out)

        secret = Secret.objects.first()
        self.assertIsNotNone(secret)
        self.assertEqual(secret.kind, "SensitiveFile (.key)")
        self.assertEqual(secret.git_source.repo_url, expected_repo_url)

    @patch('subprocess.run')
    def test_error_handling(self, mock_run):
        """Test handling of git command errors"""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd')

        out = StringIO()
        call_command('import_git_secrets', self.repo_path, f'--org={self.org}', stdout=out)

        self.assertIn("Error scanning git history", out.getvalue())
        self.assertEqual(Secret.objects.count(), 0)

    def test_sensitive_file_detection(self):
        """Test detection of sensitive file extensions"""
        test_files = [
            "config.env",
            "secret.key",
            "cert.pem",
            "not_sensitive.txt"
        ]

        sensitive_extensions = [
            ".env", ".key", ".pem", ".jks", ".p12", ".pfx", ".crt", ".cer",
            ".keystore", ".csr", ".der", ".spc", ".mobileprovision", ".keychain",
            ".provisionprofile", ".apk.sign", ".aab.sign", ".conf", ".config",
            ".ini", ".properties", ".secret", ".secrets", ".credentials", ".creds",
            ".htpasswd", ".netrc", ".aws", ".npmrc", ".tfstate", ".tfvars"
        ]
        
        sensitive_files = [
            f for f in test_files 
            if any(f.lower().endswith(ext.lower()) for ext in sensitive_extensions)
        ]
        
        self.assertIn("config.env", sensitive_files)
        self.assertIn("secret.key", sensitive_files)
        self.assertIn("cert.pem", sensitive_files)
        self.assertNotIn("not_sensitive.txt", sensitive_files)

    def tearDown(self):
        os.rmdir(self.repo_path)
        Secret.objects.all().delete()
        SecretLocation.objects.all().delete()
        GitSource.objects.all().delete()