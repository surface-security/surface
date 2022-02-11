import itertools
from . import hosts, ips
from .base import BaseInput


class IPsHosts(BaseInput):
    name = 'IPSHOSTS'
    label = 'External IPs and Hosts'

    def generate(self, **kwargs):
        """
        :return: iterator with all external IPs and DNSRecords (A, LB, CNAME)
        """
        return itertools.chain(ips.IPs().generate(**kwargs), hosts.Hosts().generate(**kwargs))


class IPsHosts(BaseInput):
    name = 'IPSHOSTSINT'
    label = 'Internal IPs and Hosts'

    def generate(self, **kwargs):
        """
        :return: iterator with all external IPs and DNSRecords (A, LB, CNAME)
        """
        return itertools.chain(ips.IPs().generate(internal=True, **kwargs), hosts.Hosts().generate(internal=True, **kwargs))
