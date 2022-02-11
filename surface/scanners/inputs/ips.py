from .base import BaseInput
from dns_ips import models


class IPs(BaseInput):
    name = 'IPS'
    label = 'External IPs'

    def generate(self, internal=False):
        """
        :param internal: if it's exposed internally or externally.
        :return: iterator with all IPs
        """
        tag_internal_or_external = 'is_external'
        if internal:
            tag_internal_or_external = 'is_internal'
        yield from (
            models.IPAddress.objects.exclude(tags__name='scan_excluded')
            .filter(active=True, tags__name=tag_internal_or_external)
            .values_list('name', flat=True)
            .distinct()
        )


class IPsInt(IPs):
    """
    ToDo: once input generators can receive parameters, this no longer makes sense :soon:
    """
    name = 'IPSINT'
    label = 'Internal IPs'

    def generate(self, *a, **b):
        """
        :return: iterator with all IPs
        """
        yield from super().generate(internal=True)
