from dns_ips import models as dns_models
from scanners import models

from .base import BaseInput


class TestHosts(BaseInput):
    name = 'TESTHOSTS'
    label = 'LiveHosts with TEST tag (on DNSRecord)'

    def generate(self):
        """
        :return: iterator with all LiveHosts linked to a record with TEST tag
        """
        return (str(host) for host in models.LiveHost.objects.filter(host__any__tags__name='test'))


class TestRecords(BaseInput):
    name = 'TESTRECORDS'
    label = 'DNS Records with TEST tag'

    def generate(self):
        """
        :return: iterator with all DNSRecords with TEST tag
        """
        return (host.name for host in dns_models.DNSRecord.objects.filter(tags__name='test'))


class TestIPs(BaseInput):
    name = 'TESTIPS'
    label = 'IP Addresses and ranges with TEST tag'

    def generate(self):
        """
        :return: iterator with all DNSRecords with TEST tag
        """
        return (ip.name for ip in dns_models.IPAddress.objects.filter(tags__name='test'))
