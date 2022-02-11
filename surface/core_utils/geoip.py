import os
import time
from tempfile import gettempdir

import pygeoip
import requests
from django.utils.functional import LazyObject

ARTIFACTORY_URL = 'https://artifactory-prd.prd.betfair/artifactory/geoip/'


# TODO: Save this in NFS + cron for updates
# TODO: use a DB that supports IPv6
def download_geoip_db(geo_db):
    file_name = os.path.join(gettempdir(), geo_db)
    # Save file only once per day
    if not os.path.exists(file_name) or int(time.time() - os.path.getmtime(file_name)) > 86400:
        with open(file_name, 'wb') as fileobj:
            fileobj.write(requests.get(ARTIFACTORY_URL + geo_db).content)

    return pygeoip.GeoIP(file_name)


# using lazy evalutation to prevent all processes to start downloading at same time
# also, makes it easier to test
# LazyObject subclass used instead of lazy() for caching first execution
class LazyGeoIP(LazyObject):
    def __init__(self, filename):
        self.__dict__['_filename'] = filename
        super().__init__()

    def _setup(self):
        self._wrapped = download_geoip_db(self._filename)


geoip = LazyGeoIP('GeoIP.dat')
geoip_isp = LazyGeoIP('GeoIPISP.dat')


def country_name(addr):
    return geoip.country_name_by_addr(addr)


def org_name(addr):
    return geoip_isp.org_by_addr(addr)
