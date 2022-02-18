import tempfile
from pathlib import Path

from django.test import TestCase

from scanners.tests import ScannerTestMixin
from scanners import models as scanner_models


class Test(ScannerTestMixin, TestCase):
    def setUp(self):
        self.setUpScanner(input='IPSHOSTS', parser='BASELINE_RESULTS', image='baseline', name='baseline')

    def _run_it(self, n80='output_80.json', n443='output_443.json'):
        tmp_dir = Path(tempfile.mkdtemp())
        st = tmp_dir / '1'
        st.mkdir()
        self._asset_copy(f'data/{n80}', st / n80)
        self._asset_copy(f'data/{n443}', st / n443)
        try:
            self._parse_results(tmp_dir)
        finally:
            self._clean(tmp_dir)

    def test_parser_no_record(self):
        with self.assertLogs(logger='scanner_baseline.scanners', level='ERROR') as cm:
            self._run_it()
        self.assertEqual(
            cm.output,
            [
                'ERROR:scanner_baseline.scanners:cannot create livehost with invalid host: www.winzip.com',
                'ERROR:scanner_baseline.scanners:cannot create livehost with invalid host: www.winzip.com',
            ],
        )
        # none created as hostname does not exist
        self.assertEqual(scanner_models.LiveHost.objects.count(), 0)

    def test_parser(self):
        self._create_dnsrecord(name='www.winzip.com')
        self._run_it()
        self.assertEqual(scanner_models.LiveHost.objects.count(), 2)
        self.assertEqual(scanner_models.LiveHost.objects.filter(port=80).count(), 1)
        self.assertEqual(scanner_models.LiveHost.objects.filter(port=443).count(), 1)

        w = scanner_models.LiveHost.objects.filter(port=80).first()
        self.assertEqual(
            w.redirects,
            '''\
https://www.winzip.com
https://www.winzip.com/mac/en/''',
        )
        self.assertEqual(
            w.cookies,
            '''\
AWSALB=i508iLnVjzJyZak72WSYT7O0dmDwQfb4oqTrIr4NJKD5rrAd9r7mT68xsibXrkPMc7PsgQn1Cic365ZfFq9uMwH2B+6KuyzzAFw1BtVxSA/q1t3g7uTHGktES3y/; Expires=Mon, 24 May 2021 14:55:51 GMT; Path=/
AWSALBCORS=i508iLnVjzJyZak72WSYT7O0dmDwQfb4oqTrIr4NJKD5rrAd9r7mT68xsibXrkPMc7PsgQn1Cic365ZfFq9uMwH2B+6KuyzzAFw1BtVxSA/q1t3g7uTHGktES3y/; Expires=Mon, 24 May 2021 14:55:51 GMT; Path=/; SameSite=None
AWSALB=NK7/Cji1tOC2Og3LQGdaP5QrZJ3PKRYud/JQWwQEqa6pdIx7YKL9v6WZ8CiId5dE547KUbmywsSy27BCduQuas53fT75R3b0QrJiT2TevgdUzfiXmyblAuG/jVIk; Expires=Mon, 24 May 2021 14:55:52 GMT; Path=/
AWSALBCORS=NK7/Cji1tOC2Og3LQGdaP5QrZJ3PKRYud/JQWwQEqa6pdIx7YKL9v6WZ8CiId5dE547KUbmywsSy27BCduQuas53fT75R3b0QrJiT2TevgdUzfiXmyblAuG/jVIk; Expires=Mon, 24 May 2021 14:55:52 GMT; Path=/; SameSite=None; Secure
AWSALB=O5iHoWdpWQwUeBnkzHu/x75n5Xy5ReJI8ohJ2jmTn3Vv4CNxZ8+cywVF8WoTrxU6y0zItt8F2wVHAjADIFIuQCt4vau2Rhgvz2cRqA6Xik8SMHvbmhTL+oaOZyhv; Expires=Mon, 24 May 2021 14:55:52 GMT; Path=/
AWSALBCORS=O5iHoWdpWQwUeBnkzHu/x75n5Xy5ReJI8ohJ2jmTn3Vv4CNxZ8+cywVF8WoTrxU6y0zItt8F2wVHAjADIFIuQCt4vau2Rhgvz2cRqA6Xik8SMHvbmhTL+oaOZyhv; Expires=Mon, 24 May 2021 14:55:52 GMT; Path=/; SameSite=None; Secure
AWSALB=O5iHoWdpWQwUeBnkzHu/x75n5Xy5ReJI8ohJ2jmTn3Vv4CNxZ8+cywVF8WoTrxU6y0zItt8F2wVHAjADIFIuQCt4vau2Rhgvz2cRqA6Xik8SMHvbmhTL+oaOZyhv; Expires=Mon, 24 May 2021 14:55:52 GMT; Path=/
AWSALBCORS=O5iHoWdpWQwUeBnkzHu/x75n5Xy5ReJI8ohJ2jmTn3Vv4CNxZ8+cywVF8WoTrxU6y0zItt8F2wVHAjADIFIuQCt4vau2Rhgvz2cRqA6Xik8SMHvbmhTL+oaOZyhv; Expires=Mon, 24 May 2021 14:55:52 GMT; Path=/; SameSite=None; Secure''',
        )
        self.assertEqual(w.final_url, 'https://www.winzip.com/mac/en/')
        self.assertEqual(w.timing, '1.48609208s')

    def test_parser_technologies(self):
        self.test_parser()
        self.assertEqual(scanner_models.Technology.objects.count(), 6)

        l80 = scanner_models.LiveHost.objects.filter(port=80).first()
        self.assertEqual(
            {x.name for x in l80.technologies.all()},
            {"mod_wsgi", "Python", "Apache", "Debian", "Amazon ALB", "Amazon Web Services"},
        )
        self._run_it(n80='output_80_rescan.json')
        self.assertEqual(scanner_models.Technology.objects.count(), 7)
        self.assertEqual(
            {x.name for x in l80.technologies.all()},
            {"mod_wsgi", "Rails", "Apache", "Amazon ALB", "Amazon Web Services"},
        )

    def test_parser_inactive(self):
        self.test_parser()
        self.assertEqual(scanner_models.LiveHost.objects.filter(active=True).count(), 2)
        self._run_it(n443="output_443_inactive.json")
        self.assertEqual(scanner_models.LiveHost.objects.filter(port=443, active=False).count(), 1)
        self._run_it()
        self.assertEqual(scanner_models.LiveHost.objects.filter(port=443, active=True).count(), 1)
