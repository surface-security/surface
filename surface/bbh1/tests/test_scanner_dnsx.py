from pathlib import Path
import tempfile

from django.test import TestCase

from scanners.tests import ScannerTestMixin
from scanners.inputs.base import query as input_query

from dns_ips import models as dns_models
from bbh1 import models


class TestDNSRecords(ScannerTestMixin, TestCase):
    def setUp(self):
        self._s1 = dns_models.DNSRecord.objects.create(name='example.com')
        self._s2 = dns_models.DNSRecord.objects.create(name='www.example.com')
        self._s2.dnsrecordvalue_set.create(rtype=dns_models.DNSRecordValue.RecordType.CNAME, value='www.google.com')

    def generate_input(self, input, *args, **kwargs):
        return list(input_query(input)().generate(*args, **kwargs))

    def test_inp_dnsrecs(self):
        self.assertEqual(
            self.generate_input('DNSRECS'),
            [
                'example.com',
                'www.example.com',
            ],
        )

    def test_inp_dnsrecs_no_values(self):
        self.assertEqual(
            self.generate_input('DNSRECS_NOVAL'),
            [
                'example.com',
            ],
        )


class TestParser(ScannerTestMixin, TestCase):
    def setUp(self):
        self.setUpScanner(input='DNSRECS', parser='DNSX', image='x', name='x')
        self._s1 = dns_models.DNSRecord.objects.create(name='example.com')
        self._s2 = dns_models.DNSRecord.objects.create(name='www.example.com')
        self._s2.dnsrecordvalue_set.create(
            rtype=dns_models.DNSRecordValue.RecordType.CNAME, value='www.google.com', active=True
        )
        self._s3 = dns_models.DNSRecord.objects.create(name='completely-made-up.example.com')

    def _run_it(self, asset='dnsx_example.json'):
        tmp_dir = Path(tempfile.mkdtemp())
        st = tmp_dir / '1'
        st.mkdir()
        self._asset_copy(f'data/{asset}', st / asset)
        try:
            self._parse_results(tmp_dir)
        finally:
            self._clean(tmp_dir)

    def test_parser(self):
        self._run_it()
        self.assertEqual(dns_models.DNSRecord.objects.count(), 3)
        self.assertEqual(self._s1.dnsrecordvalue_set.count(), 2)
        self.assertEqual(self._s2.dnsrecordvalue_set.count(), 6)
        self.assertEqual(self._s2.dnsrecordvalue_set.filter(active=True).count(), 5)
        self.assertEqual(self._s3.dnsrecordvalue_set.count(), 0)
        self.assertEqual(dns_models.DNSRecordValue.objects.count(), 8)
