import datetime
import logging
import re
from urllib.parse import urlencode

import netaddr
from django.conf import settings
from django.contrib.admin.sites import site
from django.db.models import Model
from django.urls import reverse

from dns_ips.models import DNSDomain, DNSRecord
from slackbot.base import MessageProcessor

logger = logging.getLogger(__name__)


class DNSIPSProcessor(MessageProcessor):
    CACHE_EXPIRATION = datetime.timedelta(minutes=60)
    IGNORED_TERMS = ['1.1.1.1', '127.0.0.1', 'internal', 'localhost']
    IPS_MODELS = [
        'dns_ips.iprange',
        'dns_ips.ipaddress',
        'dns_ips.dnsrecord',
    ]
    DOMAINS_MODELS = ['dns_ips.dnsdomain']
    DNS_RECORDS_MODELS = ['dns_ips.dnsrecord']

    def __init__(self, *args, **kw) -> None:
        super().__init__(*args, **kw)
        self.last_fetch = None
        self.domains = []
        self.dns_records = []

    def handle(self, message, user=None, channel=None, ts=None, raw=None):
        if not message:
            return
        self.check_cache()

        processed = self._handle_ips(message, user, channel, ts)
        processed |= self._handle_dns(message, user, channel, ts)
        if processed:
            return self.PROCESSED

    def _handle_ips(self, message, user, channel, ts):
        processed = False
        # Nice to have: Context based IP matching
        # https://realpython.com/natural-language-processing-spacy-python/#dependency-parsing-using-spacy
        # Search for details about IPs
        ips = re.findall(r'[0-9]+(?:\.[0-9]+){3}', message)
        # Limit the processed number of IPs
        limit = 3
        for ip in ips:
            if limit == 0:
                break
            if ip in self.IGNORED_TERMS:
                continue
            try:
                ip_value = str(netaddr.IPAddress(ip))
                processed = True
                self.process_terms(ip_value, channel, ts, user, self.IPS_MODELS)
            except Exception:
                pass
            limit -= 1
        return processed

    def _handle_dns(self, message, user, channel, ts):
        processed = False
        words = message.split(' ')
        # Process Domains
        for domain in self.domains:
            domain = domain.strip()
            if domain in self.IGNORED_TERMS:
                continue
            if len(domain) and domain in words:
                processed = True
                self.process_terms(domain, channel, ts, user, self.DOMAINS_MODELS)

        # Process DNS Records
        for dns_record in self.dns_records:
            dns_record = dns_record.strip()
            if dns_record in self.IGNORED_TERMS:
                continue
            if len(dns_record) and dns_record in words:
                processed = True
                self.process_terms(dns_record, channel, ts, user, self.DNS_RECORDS_MODELS)

        return processed

    def check_cache(self):
        if self.last_fetch is None or datetime.datetime.now() - self.last_fetch > self.CACHE_EXPIRATION:
            self.domains = self.fetch_domains()
            self.dns_records = self.fetch_dns_records()
            self.last_fetch = datetime.datetime.now()

    def fetch_dns_records(self):
        try:
            return list(DNSRecord.objects.filter(active=True).values_list('name', flat=True).distinct())
        except Exception as ex:
            logger.error(f'Could not fetch new things from database: {ex}')
            return self.dns_records

    def fetch_domains(self):
        try:
            return list(DNSDomain.objects.filter(active=True).values_list('name', flat=True).distinct())
        except Exception as ex:
            logger.error(f'Could not fetch new things from database: {ex}')
            return self.domains

    def process_search(self, model_class, model_admin, term, channel, ts, user):
        if not model_admin.search_fields:
            return

        # allow customization for slack and fallback to admin default search
        search_method = getattr(model_admin, 'get_slack_search_results', model_admin.get_search_results)
        safe_display = getattr(model_admin, 'slack_display_name', False)

        results, _ = search_method(None, model_class.objects.all(), term)
        if results.exists():
            count = results.count()
            model_class_name = model_class._meta.verbose_name if count == 1 else model_class._meta.verbose_name_plural
            msg = [f'Found {count} {model_class_name} with `{term}`']
            # https://api.slack.com/docs/message-formatting
            # Show only first 5 results
            for result in results[:5]:
                url = get_admin_url(result)
                result_display = url
                if "slack_display" in dir(result):
                    result_display = result.slack_display()
                elif safe_display:
                    result_display = result
                result_display = str(result_display).replace('_', ' ').replace('\n', '').replace('\r', '')
                msg.append(f'- <{str(url)}|{result_display}>.')
            url, q = str(get_admin_url(model_class)), str(urlencode({'q': term}))
            msg.append(f'Full results: <{url}?{q}|here>.')
            self.post_message(channel=channel, text='\n'.join(msg), thread_ts=ts)
            return count

    def process_terms(self, term, channel, ts, user, searched_models):
        for model_class, model_admin in site._registry.items():
            mmodel = f'{model_class._meta.app_label}.{model_class._meta.model_name}'
            if mmodel in searched_models:
                self.process_search(model_class, model_admin, term, channel, ts, user)


def get_admin_url(model):
    if isinstance(model, Model):
        args = (model.pk,)
        view = 'change'
    else:
        args = None
        view = 'changelist'
    base_hostname = settings.BASE_HOSTNAME if settings.BASE_HOSTNAME[-1] != '/' else settings.BASE_HOSTNAME[:-1]
    change_url_type = reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_{view}', args=args)
    return f'{base_hostname}{change_url_type}'
