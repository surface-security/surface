import json
import logging
from datetime import datetime
from pathlib import Path

from scanners.parsers.base import BaseParser

from scanners import models
from dns_ips import models as dns_models

logger = logging.getLogger(__name__)


class Baseline(BaseParser):
    name = 'BASELINE_RESULTS'
    label = 'Baseline'

    def _parse_headers(self, data):
        redirects = []
        cookies = []
        headers = []
        for c in data.get('chain', []):
            for l in c['response'].splitlines():
                if l.lower()[:9] == 'location:':
                    redirects.append(l[9:].strip())
                if l.lower()[:11] == 'set-cookie:':
                    cookies.append(l[11:].strip())
        for l in data.get('response-header', '').splitlines():
            if l.lower()[:11] == 'set-cookie:':
                cookies.append(l[11:].strip())
            else:
                headers.append(l)
        return redirects, cookies, headers
    
    def _find_host_record(self, hostname):
        # in a method for easier subclassing
        obj = (
            dns_models.DNSRecord.objects.filter(name=hostname).first()
            or dns_models.IPAddress.objects.filter(name=hostname).first()
        )
        if obj is None:
            logger.error('cannot create livehost with invalid host: %s', hostname)
        return obj

    def _parse_record(self, obj, rootbox, scanner, baseline_data):
        redirects, cookies, headers = self._parse_headers(baseline_data)
        active = not baseline_data.get('failed', False)
        defaults = {
            'rootbox': rootbox,
            'scanner': scanner,
            'timing': baseline_data.get('response-time'),
        }
        if active:
            defaults['status_code'] = baseline_data['status-code']
            defaults['final_url'] = baseline_data['final-url']
            defaults['headers'] = '\n'.join(headers)
            defaults['cookies'] = '\n'.join(cookies)
            defaults['redirects'] = '\n'.join(redirects) or None
            defaults['body_response'] = baseline_data.get('response-body')

        rec, created = models.LiveHost.objects.update_or_create(
            host=obj,
            port=baseline_data['port'],
            defaults=defaults,
        )
        if (rec.active is False and active is False) or created:
            source = f'{models.LiveHost._meta.app_label}.{models.LiveHost._meta.object_name}'
            title = f"Port {rec.port} is open on {rec.host}. {datetime.now().strftime('%d/%m/%Y')}"
            logger.info(f"Creating alert for SOC: {title}")
            # soc.create_incident(
            #     brand="ppb",
            #     source_id=rec.id,
            #     source=source,
            #     severity="Medium",
            #     title=title,
            #     family="external",
            #     alert_body=title,
            #     ticket_details={
            #         'discovery_method': 'rootbox',
            #     },
            #     draft=True,
            # )
        if not created:
            rec.active = active
            rec.save()
        return rec

    def _parse_file(self, rootbox, scanner, filepath):
        baseline_data = json.loads(filepath.read_text())
        obj = self._find_host_record(baseline_data['domain'])
        if obj is None:
            return
        rec = self._parse_record(obj, rootbox, scanner, baseline_data)
        self._parse_tech(rec, baseline_data)
    
    def _parse_tech(self, rec, baseline_data):
        techs = baseline_data.get('technologies', [])
        if techs:
            tech_objs = list(models.Technology.objects.filter(name__in=techs))
            # create new ones, if any
            _s = {x.name for x in tech_objs}
            new = [models.Technology(name=x) for x in techs if x not in _s]
            if new:
                new_objs = models.Technology.objects.bulk_create(new)
                # PK might not be returned... if so, extra query...
                if new_objs:
                    if new_objs[0].pk is None:
                        tech_objs = list(models.Technology.objects.filter(name__in=techs))
                    else:
                        tech_objs.extend(new_objs)
            rec.technologies.set(tech_objs)
        else:
            rec.technologies.clear()

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

        for _sf in filepath.glob('*'):
            self._parse_file(rootbox, scanner, _sf)

    def save_results(self, name, file_src):
        """
        do not pollute raw_results
        """
