from .base import BaseInput


class Hosts(BaseInput):
    name = 'HOSTS'
    label = 'External Hosts'

    def generate(self, internal=False, **kwargs):
        """
        :param internal: if it's exposed internally or externally.
        :param kwargs:
        :return: iterator with all Hosts/DNS Records (A, LB, CNAME)
        """
        from dns_ips.models import DNSRecord

        tag_internal_or_external = 'is_external'
        if internal:
            tag_internal_or_external = 'is_internal'
        yield from (
            DNSRecord.objects.exclude(tags__name='scan_excluded')
            .filter(
                active=True,
                dnsrecordvalue__active=True,
                dnsrecordvalue__rtype__in=['A', 'LB', 'CNAME'],
                tags__name=tag_internal_or_external,
            )
            .values_list('name', flat=True)
            .distinct()
        )


class HostsInt(Hosts):
    name = 'HOSTSINT'
    label = 'Internal Hosts'

    def generate(self, **kwargs):
        return super().generate(internal=True, **kwargs)
