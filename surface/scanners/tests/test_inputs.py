from django.test import TestCase
from django.utils import timezone

from scanners.inputs.base import query as input_query
from scanners.tests import ScannerTestMixin


class Base(ScannerTestMixin, TestCase):
    INP = None
    INP_IPS = False
    INP_HOSTS = True

    def setUp(self):
        self.tag_ext = self._create_tag(name='is_external')
        self.tag_int = self._create_tag(name='is_internal')
        self.tag_exc = self._create_tag(name='scan_excluded')

        if self.INP_HOSTS:
            self.d1 = self._create_dnsrecord(name='w1.betfair.com')
            self.d1.tags.add(self.tag_ext)
            self.d1.dnsrecordvalue_set.create(rtype='A')
            self.d1.dnsrecordvalue_set.create(rtype='CNAME')

            self.d2 = self._create_dnsrecord(name='w1.prd.betfair')
            self.d2.tags.add(self.tag_int)
            self.d2.dnsrecordvalue_set.create(rtype='A')

        if self.INP_IPS:
            self.ip1 = self._create_ipaddress(name='1.1.1.1')
            self.ip1.tags.add(self.tag_ext)
            self.ip2 = self._create_ipaddress(name='10.0.0.1')
            self.ip2.tags.add(self.tag_int)

    def generate_input(self, *args, **kwargs):
        return list(input_query(self.INP)().generate(*args, **kwargs))


class TestHosts(Base):
    INP = 'HOSTS'

    def test_inp(self):
        self.assertEqual(self.generate_input(), ['w1.betfair.com'])
        self.assertEqual(self.generate_input(internal=True), ['w1.prd.betfair'])
        self.d2.tags.add(self.tag_exc)
        self.assertEqual(self.generate_input(internal=True), [])


class TestIPs(Base):
    INP = 'IPS'
    INP_IPS = True
    INP_HOSTS = False

    def test_inp(self):
        self.assertEqual(self.generate_input(), ['1.1.1.1'])
        self.assertEqual(self.generate_input(internal=True), ['10.0.0.1'])
        self.ip2.tags.add(self.tag_exc)
        self.assertEqual(self.generate_input(internal=True), [])


class TestIPsNHosts(Base):
    INP = 'IPSHOSTS'
    INP_IPS = True

    def test_inp(self):
        self.assertEqual(self.generate_input(), ['1.1.1.1', 'w1.betfair.com'])
        self.ip1.tags.add(self.tag_exc)
        self.assertEqual(self.generate_input(), ['w1.betfair.com'])


class TestLive(Base):
    INP = 'LIVE'
    INP_IPS = True

    def test_inp(self):
        self._create_livehost(host=self.d1)

        # excluded, non web port
        self._create_livehost(host=self.ip1, port=9999)

        # excluded, internal
        self._create_livehost(host=self.ip2)

        # excluded, too old
        l2 = self._create_livehost(host=self.d2)
        # cheat auto_now...!
        l2.__class__.objects.filter(pk=l2.pk).update(last_seen=timezone.now() - timezone.timedelta(days=50))

        self.assertEqual(self.generate_input(), ['https://w1.betfair.com'])


class TestLiveInt(Base):
    INP = 'LIVEINT'
    INP_IPS = True

    def test_inp(self):
        # excluded, external
        self._create_livehost(host=self.d1)
        self._create_livehost(host=self.ip1)

        # internal
        x1 = self._create_livehost(host=self.d2)
        x2 = self._create_livehost(host=self.ip2)

        self.assertEqual(
            self.generate_input(),
            [
                str(x1),
                str(x2),
            ],
        )


class TestTestHosts(Base):
    INP = 'TESTHOSTS'

    def test_inp(self):
        tag = self._create_tag(name='test')
        self.d2.tags.add(tag)
        self._create_livehost(host=self.d1)
        self._create_livehost(host=self.d2)
        self.assertEqual(self.generate_input(), ['https://w1.prd.betfair'])


class TestTestRecords(Base):
    INP = 'TESTRECORDS'

    def test_inp(self):
        tag = self._create_tag(name='test')
        self.d2.tags.add(tag)
        self.assertEqual(self.generate_input(), ['w1.prd.betfair'])


class TestTestIPs(Base):
    INP = 'TESTIPS'
    INP_IPS = True
    INP_HOSTS = False

    def test_inp(self):
        tag = self._create_tag(name='test')
        self.ip1.tags.add(tag)
        self.assertEqual(self.generate_input(), ['1.1.1.1'])
