import json

from logbasecommand.base import LogBaseCommand

from pathlib import Path

from bbh1 import models


class Command(LogBaseCommand):
    help = 'Import data from masset'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=Path, help='path to export file')

    def handle(self, *args, **options):
        with options['filename'].open() as f:
            for l in f:
                obj = json.loads(l)
                models.Scope.objects.update_or_create(
                    name=obj['name'],
                    defaults={
                        'description': obj['description'],
                        'link': obj['link'],
                        'monitor': obj['monitor'],
                        'torify': obj['torify'],
                        'disabled': obj['disabled'],
                        'big_scope': obj['big_scope'],
                        'scope_domains_in': '\n'.join(obj['scope_domains_in']) if obj['scope_domains_in'] else None,
                        'scope_domains_out': '\n'.join(obj['scope_domains_out']) if obj['scope_domains_out'] else None,
                        'ignore_domains': '\n'.join(obj['ignore_domains']) if obj['ignore_domains'] else None,
                    }
                )
