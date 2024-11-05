import json
import tempfile
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from secretsmanager.models import Secret, SecretLocation
from inventory.models import GitSource

class ImportSecretsCommandTest(TestCase):
    def setUp(self):
        self.repo_url = "https://github.com/test/repo"
        self.sample_secret = {
            "Raw": "test_secret_value",
            "SourceName": "git",
            "DetectorName": "AWS Key",
            "Verified": True,
            "SourceMetadata": {
                "Data": {
                    "Git": {
                        "file": "config/secrets.yml",
                        "commit": "abc123",
                        "repository": self.repo_url,
                        "author": "test@example.com",
                        "line": "42"
                    }
                }
            }
        }

    def create_temp_json(self, data):
        """Helper to create a temporary JSON file with test data"""
        temp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        json.dump(data, temp)
        temp.write('\n')
        temp.close()
        return temp.name

    def test_import_valid_secret(self):
        """Test importing a valid secret from JSON"""
        json_file = self.create_temp_json(self.sample_secret)
        
        out = StringIO()
        call_command('import_secrets', json_file, stdout=out)

        secret = Secret.objects.first()
        self.assertIsNotNone(secret)
        self.assertEqual(secret.secret, "test_secret_value")
        self.assertEqual(secret.kind, "AWS Key")
        self.assertTrue(secret.verified)

        location = SecretLocation.objects.first()
        self.assertIsNotNone(location)
        self.assertEqual(location.file_path, "config/secrets.yml")
        self.assertEqual(location.commit, "abc123")
        self.assertTrue(location.timestamp)

        git_source = GitSource.objects.first()
        self.assertIsNotNone(git_source)
        self.assertEqual(git_source.repo_url, self.repo_url)

    def test_import_invalid_json(self):
        """Test handling of invalid JSON"""
        temp = tempfile.NamedTemporaryFile(mode='w', delete=False)
        temp.write('invalid json content\n')
        temp.close()

        out = StringIO()
        call_command('import_secrets', temp.name, stdout=out)

        self.assertIn("Error decoding JSON", out.getvalue())

        self.assertEqual(Secret.objects.count(), 0)
        self.assertEqual(SecretLocation.objects.count(), 0)

    def test_import_duplicate_secret(self):
        """Test importing the same secret twice"""
        json_file = self.create_temp_json(self.sample_secret)

        call_command('import_secrets', json_file)
        call_command('import_secrets', json_file)

        self.assertEqual(Secret.objects.count(), 1)
        self.assertEqual(SecretLocation.objects.count(), 1)

    def tearDown(self):
        Secret.objects.all().delete()
        SecretLocation.objects.all().delete()
        GitSource.objects.all().delete()