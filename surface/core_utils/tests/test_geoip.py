import shutil
import tempfile

from unittest import mock
from django.test import TestCase

from core_utils import geoip


class Test(TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.temppatch = mock.patch('core_utils.geoip.gettempdir')
        self.tempmock = self.temppatch.start()
        self.tempmock.return_value = self.tmp_dir

    def tearDown(self):
        self.temppatch.stop()
        shutil.rmtree(self.tmp_dir)

    @mock.patch('requests.get')
    @mock.patch('pygeoip.GeoIP')
    def test_geoip_country(self, gip, rp):
        rp.return_value = mock.MagicMock(content=b'')
        gip().country_name_by_addr.return_value = 'United Kingdom'
        self.assertEqual(geoip.country_name('84.20.200.28'), 'United Kingdom')
        gip().country_name_by_addr.assert_called_with('84.20.200.28')
        rp.assert_called_with('https://artifactory-prd.prd.betfair/artifactory/geoip/GeoIP.dat')

        # file saved?
        rp.reset_mock()
        self.assertEqual(geoip.country_name('84.20.200.28'), 'United Kingdom')
        rp.assert_not_called()

    @mock.patch('requests.get')
    @mock.patch('pygeoip.GeoIP')
    def test_geoip_org(self, gip, rp):
        rp.return_value = mock.MagicMock(content=b'')
        gip().org_by_addr.return_value = 'The Sporting Exchange Ltd'
        self.assertEqual(geoip.org_name('84.20.200.28'), 'The Sporting Exchange Ltd')
        gip().org_by_addr.asset_called_with('84.20.200.28')
        rp.assert_called_with('https://artifactory-prd.prd.betfair/artifactory/geoip/GeoIPISP.dat')
