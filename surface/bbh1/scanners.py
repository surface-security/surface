from pathlib import Path
import json

from django.utils import timezone

from scanners.inputs.base import BaseInput
from scanners.parsers.base import BaseParser

from dns_ips import models as dns_models
from .models import Scope


class Scopes(BaseInput):
    name = 'BBH1SCOPES'
    label = 'BBH1 Scopes'

    def queryset(self):
        return Scope.objects.filter(disabled=False)

    def generate(self):
        yield from (
            json.dumps(
                {
                    'name': x.name,
                    'domains': x.clean_domains(all=True),
                }
            )
            for x in self.queryset()
        )


class MonitoredScopes(Scopes):
    name = 'BBH1SCOPESMON'
    label = 'BBH1 Scopes (Monitored)'

    def queryset(self):
        return Scope.objects.filter(disabled=False, monitor=True)


class Subfinder(BaseParser):
    name = 'SUBFINDER'
    label = 'Subfinder'

    def _parse_file(self, rootbox, scanner, filepath):
        source, _ = dns_models.Source.objects.get_or_create(name=f'bb1_{filepath.stem}')
        with filepath.open('r') as f:
            for rec in f:
                obj = json.loads(rec)
                dns_models.DNSRecord.objects.update_or_create(
                    source=source, name=obj['host'], defaults={'last_seen': self.timestamp_dt}
                )

    def parse(self, rootbox, scanner, timestamp, filepath):
        """
        handler for baseline results

        :param rootbox:
        :param scanner:
        :param timestamp:
        :param filepath:
        :return:
        """

        filepath = Path(filepath)
        self.timestamp_dt = timezone.make_aware(timezone.datetime.fromtimestamp(int(self.timestamp)), timezone.utc)

        for _sf in filepath.glob('*'):
            self._parse_file(rootbox, scanner, _sf)

    def save_results(self, name, file_src):
        """
        do not pollute raw_results
        """
