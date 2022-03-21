from io import StringIO
from unittest import mock
from docker.errors import APIError

from django.core import management
from django.test import TestCase

from scanners import models
from scanners.management.commands import run_scanners_continuously, run_squid_proxy
from scanners.tests import ScannerTestMixin


class TestRunScannersContinuously(ScannerTestMixin, TestCase):
    def setUp(self):
        self._out = StringIO()
        self._err = StringIO()
        self._cmd = run_scanners_continuously.Command(stdout=self._out, stderr=self._err)

    @mock.patch('scanners.management.commands.run_scanners_continuously.call_command')
    def test_empty(self, call_mock):
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_not_called()

    @mock.patch('scanners.management.commands.run_scanners_continuously.call_command')
    def test_no_continous(self, call_mock):
        self._cmd.handle_loop()
        self.setUpScanner()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_not_called()

    @mock.patch('scanners.utils.check_scanners_in_box')
    @mock.patch('scanners.management.commands.run_scanners_continuously.call_command')
    def test_with_continous(self, call_mock, check_mock):
        self.setUpScanner()
        self.scanner.continous_running = True
        self.scanner.save()
        check_mock.return_value = [(f'scanner-test-999-whatever-9990', None)]
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_called_once()
        check_mock.assert_called_once_with(self.scanner.rootbox)

    @mock.patch('scanners.utils.check_scanners_in_box')
    @mock.patch('scanners.management.commands.run_scanners_continuously.call_command')
    @mock.patch('scanners.management.commands.run_scanner.Command')
    def test_with_continous_running(self, run_mock, call_mock, check_mock):
        self.setUpScanner()
        self.scanner.continous_running = True
        self.scanner.save()

        # not running, should start
        check_mock.return_value = iter([])
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_called_once_with(run_mock.return_value, self.scanner)
        check_mock.assert_called_once_with(self.scanner.rootbox)

        # already running
        check_mock.reset_mock()
        call_mock.reset_mock()
        check_mock.return_value = iter([(f'scanner-test-{self.scanner.pk}-{self.scanner.image.name}-9990', None)])
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_not_called()
        check_mock.assert_called_once_with(self.scanner.rootbox)

    @mock.patch('scanners.utils.check_scanners_in_box')
    @mock.patch('scanners.management.commands.run_scanners_continuously.call_command')
    @mock.patch('scanners.management.commands.run_scanner.Command')
    def test_with_continous_running_multiple(self, run_mock, call_mock, check_mock):
        # bug that would only consider first scanner found to check already running
        # which would result in every scanner in that rootbox, apart from first,
        # to be started multiple times
        self.setUpScanner()
        self.scanner.continous_running = True
        self.scanner.save()
        # clone it
        scanner2 = self.scanner.__class__.objects.get(pk=self.scanner.pk)
        scanner2.pk = None
        scanner2.scanner_name = 'whatever'
        scanner2.save()

        # not running, should start
        check_mock.return_value = iter([])
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        self.assertEqual(
            sorted(call_mock.call_args_list, key=lambda x: x[0][1].pk),
            [
                mock.call(run_mock.return_value, self.scanner),
                mock.call(run_mock.return_value, scanner2),
            ],
        )
        check_mock.assert_called_once_with(self.scanner.rootbox)

        # one running, start the other
        check_mock.reset_mock()
        call_mock.reset_mock()
        check_mock.return_value = iter([(f'scanner-test-{self.scanner.pk}-{self.scanner.image.name}-9990', None)])
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        self.assertEqual(
            call_mock.mock_calls,
            [
                mock.call(run_mock.return_value, scanner2),
            ],
        )
        check_mock.assert_called_once_with(self.scanner.rootbox)

        # both running
        check_mock.reset_mock()
        call_mock.reset_mock()
        check_mock.return_value = iter(
            [
                # reversed on purpose as self.scanner is checked first
                # and would iterate over scanner2 - bug if not properly cast to list before
                (f'scanner-test-{scanner2.pk}-{scanner2.image.name}-9990', None),
                (f'scanner-test-{self.scanner.pk}-{self.scanner.image.name}-9990', None),
            ]
        )
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_not_called()
        check_mock.assert_called_once_with(self.scanner.rootbox)

    @mock.patch('scanners.utils.check_scanners_in_box')
    @mock.patch('scanners.management.commands.run_scanners_continuously.call_command')
    def test_with_continous_inactive_rootbox(self, call_mock, check_mock):
        self.setUpScanner()
        self.scanner.continous_running = True
        self.scanner.save()
        self.scanner.rootbox.active = False
        self.scanner.rootbox.save()
        check_mock.return_value = [(f'scanner-test-999-whatever-9990', None)]
        self._cmd.handle_loop()
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_not_called()
        check_mock.assert_not_called()


class TestRunSquidProxy(ScannerTestMixin, TestCase):
    def setUp(self):
        self._out = StringIO()
        self._err = StringIO()
        self._cmd = run_squid_proxy.Command(stdout=self._out, stderr=self._err)

    def test_error(self):
        with self.assertRaises(models.Rootbox.DoesNotExist):
            management.call_command(self._cmd, 'test')

    @mock.patch('scanners.utils.get_docker_client')
    def test_run(self, call_mock):
        self.setUpScanner()
        client_mock = call_mock.return_value
        # no way to assert logs were NOT called...? so much for branch coverage
        with self.assertLogs(logger='surface.command.run_squid_proxy', level='WARNING') as cm:
            management.call_command(self._cmd, self.rootbox.name)
            cm.records.append('x')  # monkey wants to assert no logs
        self.assertEqual(cm.output, [])
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_called_once_with('1.1.1.1', 80, use_tls=False)
        client_mock.images.pull.assert_called_once_with('registry.com/test/squid', 'latest')
        client_mock.containers.create.assert_called_once()
        client_mock.containers.create.return_value.start.assert_called_once_with()

    @mock.patch('scanners.utils.get_docker_client')
    def test_run_pull_fail(self, call_mock):
        self.setUpScanner()
        client_mock = call_mock.return_value
        client_mock.images.pull.side_effect = APIError('wtv')
        with self.assertLogs(logger='surface.command.run_squid_proxy', level='WARNING') as cm:
            management.call_command(self._cmd, self.rootbox.name)
        self.assertEqual(cm.output, ['WARNING:surface.command.run_squid_proxy:failed to pull image: wtv'])
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_called_once_with('1.1.1.1', 80, use_tls=False)
        client_mock.images.pull.assert_called_once_with('registry.com/test/squid', 'latest')
        client_mock.containers.create.assert_called_once()
        client_mock.containers.create.return_value.start.assert_called_once_with()

    @mock.patch('scanners.utils.get_docker_client')
    def test_run_exists(self, call_mock):
        self.setUpScanner()
        client_mock = call_mock.return_value
        client_mock.containers.create.side_effect = APIError(
            '', response=mock.MagicMock(status_code=409), explanation='X is already in use by container X'
        )
        # no way to assert logs were NOT called...? so much for branch coverage
        with self.assertLogs(logger='surface.command.run_squid_proxy', level='WARNING') as cm:
            management.call_command(self._cmd, self.rootbox.name)
        self.assertEqual(cm.output, ['WARNING:surface.command.run_squid_proxy:already running in testvm'])
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_called_once_with('1.1.1.1', 80, use_tls=False)
        client_mock.images.pull.assert_called_once_with('registry.com/test/squid', 'latest')
        client_mock.containers.create.assert_called_once()

    @mock.patch('scanners.utils.get_docker_client')
    def test_run_exists_recreate(self, call_mock):
        self.setUpScanner()
        client_mock = call_mock.return_value
        container_mock = mock.MagicMock()
        client_mock.containers.create.side_effect = [
            # error on first create
            APIError('', response=mock.MagicMock(status_code=409), explanation='X is already in use by container X'),
            # pass on second create
            container_mock,
        ]
        # no way to assert logs were NOT called...? so much for branch coverage
        with self.assertLogs(logger='surface.command.run_squid_proxy', level='WARNING') as cm:
            management.call_command(self._cmd, self.rootbox.name, recreate=True)
        self.assertEqual(cm.output, ['WARNING:surface.command.run_squid_proxy:already running in testvm'])
        self.assertEqual(self._out.getvalue(), '')
        self.assertEqual(self._err.getvalue(), '')
        call_mock.assert_called_once_with('1.1.1.1', 80, use_tls=False)
        client_mock.images.pull.assert_called_once_with('registry.com/test/squid', 'latest')
        client_mock.api.remove_container.assert_called_once_with('squid-test')
        self.assertEqual(client_mock.containers.create.call_count, 2)
