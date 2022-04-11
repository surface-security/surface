from pathlib import Path
import json
import logging

from django.utils import timezone

from scanners.inputs.base import BaseInput
from scanners.parsers.base import BaseParser

from dns_ips import models as dns_models

logger = logging.getLogger(__name__)


class DNSRecords(BaseInput):
    name = 'DNSRECS'
    label = 'DNS Records'

    def queryset(self):
        return dns_models.DNSRecord.objects.all()

    def generate(self):
        yield from (x['name'] for x in self.queryset().values('name'))


class DNSRecordsWithoutValues(DNSRecords):
    name = 'DNSRECS_NOVAL'
    label = 'DNS Records (Unresolved)'

    def queryset(self):
        return dns_models.DNSRecord.objects.filter(dnsrecordvalue__isnull=True)


class DNSX(BaseParser):
    name = 'DNSX'
    label = 'DNSX'
    RTYPES = {
        'a',
        'aaaa',
        'cname',
        'ns',
        'txt',
        'ptr',
        'mx',
        'soa',
    }

    def _parse_file(self, rootbox, scanner, filepath):
        with filepath.open('r') as f:
            for rec in f:
                obj = json.loads(rec)
                host = dns_models.DNSRecord.objects.filter(name=obj['host']).first()
                if not host:
                    logger.error('unexpected hostname: %s', obj['host'])
                    continue
                values = {}
                only_soa = True
                for l in self.RTYPES:
                    for ll in obj.get(l, []):
                        if l != 'soa':
                            only_soa = False
                        values[
                            (
                                l.upper(),
                                ll,
                            )
                        ] = False
                if only_soa:
                    # ignore those with only SOA...
                    values = {}
                old_values = list(host.dnsrecordvalue_set.all())
                new_values = []
                for o in old_values:
                    if (o.rtype, o.value) in values:
                        o.active = True
                        o.last_seen = self.timestamp_dt
                        values[(o.rtype, o.value)] = True
                    else:
                        o.active = False
                for k, v in values.items():
                    if not v:
                        new_values.append(
                            dns_models.DNSRecordValue(
                                record=host,
                                rtype=k[0],
                                value=k[1],
                                active=True,
                                last_seen=self.timestamp_dt,
                            )
                        )
                dns_models.DNSRecordValue.objects.bulk_update(
                    old_values,
                    fields=['rtype', 'value', 'active', 'last_seen'],
                )
                if new_values:
                    dns_models.DNSRecordValue.objects.bulk_create(new_values)

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
