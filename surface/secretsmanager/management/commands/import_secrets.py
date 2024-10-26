import json
from django.core.management.base import BaseCommand
from secretsmanager.models import Secret


class Command(BaseCommand):
    help = 'Import secrets from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing secrets')

    def handle(self, *args, **options):
        json_file = options['json_file']

        with open(json_file, 'r') as file:
            for line in file:
                secret_data = json.loads(line)

                # Extract relevant information from the JSON data
                secret = secret_data['Raw']
                source = secret_data['SourceName']
                kind = secret_data['DetectorName']
                locations = [{
                    'repo': secret_data['SourceMetadata']['Data']['Git']['repository'],
                    'file': secret_data['SourceMetadata']['Data']['Git']['file']
                }]

                # Create or update the Secret object
                Secret.objects.update_or_create(
                    secret=secret,
                    source=source,
                    defaults={
                        'kind': kind,
                        'locations': locations,
                        'verified': secret_data['Verified'],
                        'environment': 'Unknown',  # You may want to set this based on your needs
                        'team': 'Unknown',  # You may want to set this based on your needs
                    }
                )

        self.stdout.write(self.style.SUCCESS('Successfully imported secrets'))