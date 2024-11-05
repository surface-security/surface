import json
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from datetime import datetime
from secretsmanager.models import Secret, SecretLocation
from inventory.models import GitSource

class Command(BaseCommand):
    help = 'Import secrets from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing secrets')
        parser.add_argument('--repo-url', type=str, help='Repository URL for Git scans')

    def handle(self, *args, **options):
        json_file = options['json_file']
        repo_url = options.get('repo-url')

        with open(json_file, 'r') as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                try:
                    secret_data = json.loads(line)
                except json.JSONDecodeError as e:
                    self.stdout.write(self.style.ERROR(f"Error decoding JSON: {e}"))
                    continue

                secret_value = secret_data['Raw']
                source = secret_data['SourceName']
                kind = secret_data['DetectorName']

                file_info = secret_data['SourceMetadata']['Data']['Git']
                repo_url = file_info.get('repository', repo_url)

                git_source, _ = GitSource.objects.get_or_create(
                    repo_url=repo_url,
                    defaults={'branch': 'main'}
                )

                secret, _ = Secret.objects.get_or_create(
                    secret=secret_value,
                    source=source,
                    git_source=git_source,
                    defaults={
                        'kind': kind,
                        'verified': secret_data['Verified'],
                        'environment': 'Unknown',
                        'team': 'Unknown',
                    }
                )

                SecretLocation.objects.update_or_create(
                    secret=secret,
                    file_path=file_info.get('file', 'unknown'),
                    commit=file_info.get('commit', 'unknown'),
                    defaults={
                        'repository': repo_url,
                        'timestamp': make_aware(datetime.now()),
                        'author': file_info.get('author', 'unknown'),
                        'line': str(file_info.get('line', '1'))
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully imported secrets'))