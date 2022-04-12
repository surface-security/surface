from pathlib import Path
import tempfile

from django.test import TestCase

from scanners.tests import ScannerTestMixin
from scanners.inputs.base import query as input_query

from dns_ips import models as dns_models
from bbh1 import models


class TestScopes(ScannerTestMixin, TestCase):
    def setUp(self):
        self._s1 = models.Scope.objects.create(
            name='scope1',
            scope_domains_in='google.com\nhttps://amazon.com',
            scope_domains_out='apple.com',
        )
        self._s2 = models.Scope.objects.create(
            name='scope2',
            scope_domains_in='shopify.com',
            monitor=True,
        )
        self._s3 = models.Scope.objects.create(
            name='scope3',
            disabled=True,
            scope_domains_in='netflix.com',
        )

    def generate_input(self, input, *args, **kwargs):
        return list(input_query(input)().generate(*args, **kwargs))

    def test_inp_enabled(self):
        self.assertEqual(
            self.generate_input('BBH1SCOPES'),
            [
                '{"name": "scope1", "domains": ["google.com", "amazon.com", "apple.com"]}',
                '{"name": "scope2", "domains": ["shopify.com"]}',
            ],
        )

    def test_inp_monitored(self):
        self.assertEqual(
            self.generate_input('BBH1SCOPESMON'),
            [
                '{"name": "scope2", "domains": ["shopify.com"]}',
            ],
        )


class TestParser(ScannerTestMixin, TestCase):
    def setUp(self):
        self.setUpScanner(input='SCOPES', parser='SUBFINDER', image='x', name='x')
        self._s1 = models.Scope.objects.create(
            name='example',
        )

    def _run_it(self, asset='example.json'):
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
        self.assertEqual(dns_models.DNSRecord.objects.count(), 75)
        self.assertEqual(dns_models.DNSRecord.objects.first().source.name, 'subfinder')
        self.assertEqual(dns_models.DNSRecord.objects.first().tla_id, self._s1.pk)
