import io
import os
import shutil
import sys
import tarfile

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model

from dns_ips import models as ip_models
from scanners import models
from scanners.management.commands import parse_scanner_results


class ScannerTestMixin:
    user = None
    site = None
    scanner = None
    scannerimage = None
    rootbox = None

    def setUpScanner(self, input=None, parser=None, image='docker_image', name='scanner_name', extra_args=None):
        self.scannerimage = models.ScannerImage.objects.create(name=image, image=f'registry.com/test/{image}')
        self.rootbox = models.Rootbox.objects.create(
            name='testvm', ip='1.1.1.1', ssh_user='yourmom', location='local', dockerd_tls=False
        )
        self.scanner = models.Scanner.objects.create(
            image=self.scannerimage,
            rootbox=self.rootbox,
            scanner_name=name,
            input=input,
            parser=parser,
            extra_args=extra_args,
        )
        self.user = get_user_model().objects.create_user('tester', 'tester@ppb.it', 'tester')
        self.site = AdminSite()

    def _login(self):
        self.client.login(username='tester', password='tester')

    def _clean(self, tempdir):
        try:
            shutil.rmtree(tempdir)
        except (FileNotFoundError, PermissionError):
            pass

    def _create_tag(self, name='is_external'):
        return ip_models.Tag.objects.create(name=name)

    def _create_dnsrecord(self, name='www.betfair.com'):
        return ip_models.DNSRecord.objects.create(name=name, source=ip_models.Source.objects.get(name="UNKNOWN"))

    def _create_ipaddress(self, name='1.1.1.1'):
        return ip_models.IPAddress.objects.create(name=name, source=ip_models.Source.objects.get(name="UNKNOWN"))

    def _create_livehost(self, name='www.betfair.com', port=443, host=None):
        if host is None:
            host = self._create_dnsrecord(name=name)
        return models.LiveHost.objects.create(port=port, host=host)

    def _info(self):
        return f'{self.rootbox.pk}\n{self.scanner.pk}'

    def _asset(self, name):
        # get subclass __file__ for test asset location...
        return os.path.join(os.path.dirname(sys.modules[self.__module__].__file__), name)

    def _asset_content(self, name, mode='r'):
        with open(self._asset(name), mode=mode) as f:
            return f.read()

    def _asset_copy(self, name, destination):
        if os.path.isdir(destination):
            # if target is directory, use original filename
            destination = os.path.join(destination, name)
        shutil.copyfile(self._asset(name), destination)

    def _parse_results(self, res_dir, scanner=None, rootbox=None):
        # dull method for quicker access from scanner tests
        if scanner is None:
            scanner = self.scanner
        return list(parse_scanner_results.parse_results(res_dir, scanner=scanner, rootbox=rootbox))

    def _create_tar_file(self, content_and_path_tuples):
        input_tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=input_tar_bytes, mode='w') as input_tar:
            for content, path in content_and_path_tuples:
                data = io.BytesIO()
                if isinstance(content, str):
                    data.write(content.encode())
                else:
                    data.write(content)
                info = tarfile.TarInfo(name=path)
                info.size = data.tell()
                data.seek(0)
                input_tar.addfile(tarinfo=info, fileobj=data)
        input_tar_bytes.seek(0)
        return input_tar_bytes
