from io import StringIO
from unittest import mock

from django.core import management
from django.test import TestCase

from scanners.tests import ScannerTestMixin
from scanners import models


class Test(ScannerTestMixin, TestCase):
    def setUp(self):
        self.setUpScanner(image='nmap', name='nmap1', input='IPSWHITE', parser='IP_OPEN_PORTS', extra_args='-p 1,2,3')

    def test_run_scanner_empty(self):
        out = StringIO()
        err = StringIO()

        management.call_command('run_scanner', self.scanner.scanner_name, stdout=out, stderr=err)
        self.assertEqual(out.getvalue(), 'Skipping nmap1 with empty input file\n')
        self.assertEqual(err.getvalue(), '')

    @mock.patch('django.db.close_old_connections')  # bad for test :P
    @mock.patch('scanners.utils.check_scanners_in_box')
    def test_sync_running(self, check_mock, *_):
        out = StringIO()
        err = StringIO()
        check_mock.return_value = [
            (f'scanner-test-{self.scanner.pk}-wtv-12345', mock.MagicMock(status=models.ScanLog.States.RUNNING.label)),
            ('scanner-test-99999999999-wtv-12345', mock.MagicMock(status=models.ScanLog.States.RUNNING.label)),
            ('scanner-test-wtv-12345', mock.MagicMock(status=models.ScanLog.States.RUNNING.label)),
        ]

        management.call_command('resync_rootbox', run_once=True, just='running', stdout=out, stderr=err, verbosity=2)
        self.assertEqual(
            out.getvalue(), f'Processing testvm\n{self.scanner.pk}-wtv-12345 started\n99999999999-wtv-12345 started\n'
        )
        self.assertEqual(err.getvalue(), '')

        self.assertEqual(models.ScanLog.objects.count(), 2)

        l1 = models.ScanLog.objects.get(name='99999999999-wtv-12345')
        self.assertIsNone(l1.scanner)
        self.assertEqual(l1.rootbox, self.rootbox)
        l1_seen = l1.last_seen

        l2 = models.ScanLog.objects.get(name=f'{self.scanner.pk}-wtv-12345')
        self.assertEqual(l2.scanner, self.scanner)
        self.assertEqual(l2.rootbox, self.rootbox)
        l2_seen = l2.last_seen

        out = StringIO()
        err = StringIO()
        check_mock.return_value = [
            (f'scanner-test-{self.scanner.pk}-wtv-12345', mock.MagicMock(status=models.ScanLog.States.RUNNING.label)),
        ]

        management.call_command('resync_rootbox', run_once=True, just='running', stdout=out, stderr=err, verbosity=2)
        self.assertEqual(out.getvalue(), 'Processing testvm\n')
        self.assertEqual(err.getvalue(), '')

        l1 = models.ScanLog.objects.get(name='99999999999-wtv-12345')
        self.assertEqual(l1.last_seen, l1_seen)

        l2 = models.ScanLog.objects.get(name=f'{self.scanner.pk}-wtv-12345')
        self.assertNotEqual(l2.last_seen, l2_seen)
