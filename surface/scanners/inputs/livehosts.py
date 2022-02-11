import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone

from scanners import models

from .base import BaseInput

logger = logging.getLogger(__name__)


class LiveIPsHosts(BaseInput):
    name = 'LIVE'
    label = 'External IPs and Hosts (LIVE)'

    def _queryset(self, ports, tag_filter):
        return models.LiveHost.objects.filter(
            host__any__tags__name=tag_filter,
            last_seen__gte=timezone.now() - timezone.timedelta(days=7),
            port__in=ports,
        )

    def generate(self, ports=None, internal=False, **kwargs):
        """
        :param specific_keyword:
        :param ports:
        :param extra_input:
        :param kwargs:
        :return: iterator with all external IPs and DNSRecords (A, LB, CNAME)
        """

        if ports is None:
            ports = [80, 443]
        tag_filter = 'is_internal' if internal else 'is_external'

        # A Host is live if was responding to requests in the last 7 days
        for host in (
            self._queryset(ports, tag_filter)
            .exclude(final_url='https://aws.amazon.com/s3/')
            .prefetch_related('host')
            .all()
        ):
            try:
                yield str(host)
            except (ObjectDoesNotExist, AttributeError):
                logger.error('livehost with invalid host: %d', host.pk)


class LiveIPsHostsInt(LiveIPsHosts):
    name = 'LIVEINT'
    label = 'Internal IPs and Hosts (LIVE)'

    def generate(self, **kwargs):
        return super().generate(internal=True)


class LiveIPsHostsHTTPS(LiveIPsHosts):
    name = 'LIVEHTTPS'
    label = 'External IPs and Hosts on HTTPS (LIVE)'

    def generate(self, **kwargs):
        """
        :param extra_input:
        :param specific_keyword:
        :param ports:
        :param kwargs:
        :return: iterator with all external IPs and DNSRecords (A, LB, CNAME)
        """
        return super().generate(ports=[443])
