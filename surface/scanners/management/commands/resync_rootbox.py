import os
import shutil
import tempfile
import time
import re
import tarfile
from datetime import datetime, timedelta

from django.conf import settings
from django import db

from database_locks import locked
from scanners import models, utils
from logbasecommand.base import LogBaseCommand
from scanners.management.commands.parse_scanner_results import parse_results, ParseException


@locked
class Command(LogBaseCommand):
    help = 'Run sync of data from rootbox.'

    def __init__(self, *a, **b):
        super().__init__(*a, **b)
        self.__run_match = re.compile(rf'scanner-{settings.AVZONE}-(\d+)-(.*)')
        self._helper = f'{settings.SCANNERS_IMAGE_PREFIX}helper:85'

    def add_arguments(self, parser):
        parser.add_argument('-1', '--run-once', action='store_true', default=False, help='Run only one check')
        parser.add_argument(
            '-j',
            '--just',
            choices=['results', 'running'],
            nargs='+',
            default=['results', 'running'],
            help='Fetch only logs or results (default: all)',
        )
        parser.add_argument('--delay', default=5, type=int, help='Resync interval (in seconds)')
        parser.add_argument(
            '-r', '--rootbox', nargs='+', type=str, help='Specify rootboxes to resync (defaults to all active)'
        )

    def run_helper(self, rootbox, command, remove=True, **kwargs):
        docker = utils.get_docker_client(rootbox.ip, port=rootbox.dockerd_port, use_tls=rootbox.dockerd_tls)
        try:
            out = docker.containers.run(self._helper, command=command, remove=remove, **kwargs)
        except Exception:
            self.log_exception('failed listing output files')
            return None

        if not out or not out.startswith(b'MARK\n'):
            # output should always start with 'MARK\n' otherwise log collection failed...
            self.log_error('failed listing output files...')
            return None

        return out[5:]

    def _process_files(self, rootbox, tempdir):
        docker = utils.get_docker_client(rootbox.ip, port=rootbox.dockerd_port, use_tls=rootbox.dockerd_tls)

        # download tarball with files from docker host
        c = docker.containers.create(
            self._helper, volumes={f'/scanners_{settings.AVZONE}/output/': {'bind': '/output', 'mode': 'ro'}}
        )
        tar_name = os.path.join(tempdir, 'dl.tar')
        strm, stat = c.get_archive('/output/')
        with open(tar_name, 'wb') as outfile:
            for d in strm:
                outfile.write(d)
        c.remove()

        # untar and keep track of the downloaded files for next step
        del_txt_name = os.path.join(tempdir, 'todel.txt')
        with open(del_txt_name, 'w') as files_to_delete:
            with tarfile.open(tar_name) as outfile:
                for _x in outfile:
                    if not _x.isdir():
                        files_to_delete.write(f'/{_x.name}\n')
                # TODO: trust docker API to not add the / prefix? or inspect beforehand?
                outfile.extractall(tempdir)

        # remove files from docker host
        c = docker.containers.create(
            self._helper,
            command=['clean', '/todel.txt'],
            volumes={f'/scanners_{settings.AVZONE}/output/': {'bind': '/output', 'mode': 'rw'}},
        )
        del_tar_name = os.path.join(tempdir, 'todel.tar')
        with tarfile.open(del_tar_name, "w:gz") as tar:
            tar.add(del_txt_name, arcname='todel.txt')
        with open(del_tar_name, "rb") as t:
            c.put_archive('/', t)
        c.start()
        out = c.logs()
        if out != b'MARK\n':
            self.log_error('output cleanup weird output: %s', out.decode())
        c.wait()
        c.remove()

        # TODO: this was already done after files were deleted, should it be done before? should we track per file?
        out_dir = os.path.join(tempdir, 'output')
        for _sn in os.listdir(out_dir):
            try:
                for m in parse_results(os.path.join(out_dir, _sn), rootbox=rootbox):
                    self.log(m)
            except ParseException:
                self.log_exception('parser failed')

    def handle_results(self, rootbox, tempdir):
        out = self.run_helper(
            rootbox, 'list', volumes={f'/scanners_{settings.AVZONE}/output/': {'bind': '/output', 'mode': 'ro'}}
        )
        if out:
            # nothing done with "out", as we just want to get all we can
            # and delete only the ones actually downloaded (which might be more than this output)
            self._process_files(rootbox, tempdir)

    def handle_running(self, rootbox):
        for c_name, c in utils.check_scanners_in_box(rootbox, all=True):
            m = self.__run_match.match(c_name)
            if m:
                pk = f'{m.group(1)}-{m.group(2)}'
                try:
                    scanner = models.Scanner.objects.get(pk=m.group(1))
                except models.Scanner.DoesNotExist:
                    scanner = None
                cont, created = models.ScanLog.objects.update_or_create(
                    name=pk,
                    defaults={
                        'scanner': scanner,
                        'rootbox': rootbox,
                        'state': getattr(models.ScanLog.States, c.status.upper(), None),
                    },
                )
                self.handle_logs(c, cont)
                if created:
                    self.log_debug(f'{pk} started')
                if cont.state == models.ScanLog.States.EXITED:
                    # need reload to get ExitCode
                    c.reload()
                    cont.exit_code = c.attrs['State']['ExitCode']
                    cont.save(update_fields=['exit_code'])
                    self.log_debug(f'{pk} exited, removing')
                    c.remove()

    def handle_logs(self, container, scan_log):
        last = scan_log.output_lines.order_by('-timestamp').first()
        if last is not None:
            # slight bump to avoid repeated (last) line
            last = last.timestamp + timedelta(microseconds=1)
        lines = container.logs(timestamps=True, since=last).splitlines()
        line_objs = []
        for line in lines:
            line = line.decode()
            sep = line.find(' ')
            time = line[:sep]
            text = line[sep + 1 :]
            if time[-1] != 'Z' or len(time) != 30:
                self.log_error('invalid time string', line)
            else:
                dt_time = datetime.fromisoformat(time[:-4] + '+00:00')
                self.log(f'[{scan_log.scanner}] [{dt_time.strftime("%d-%m-%y %H:%M:%S")}] {text}')
                line_objs.append(
                    models.ScanOutput(
                        log=scan_log,
                        timestamp=dt_time,
                        line=text,
                    )
                )
        models.ScanOutput.objects.bulk_create(line_objs, batch_size=100)

    def handle(self, *args, **options):
        if options['rootbox']:
            filter_kwargs = {'name__in': options['rootbox']}
        else:
            filter_kwargs = {}

        while True:
            db.close_old_connections()

            rootboxes = models.Rootbox.objects.filter(active=True, **filter_kwargs)
            for rootbox in rootboxes:
                self.log_debug('Processing %s', rootbox.name)
                tempdir = tempfile.mkdtemp()

                if 'running' in options['just']:
                    self.handle_running(rootbox)

                if 'results' in options['just']:
                    self.handle_results(rootbox, tempdir)

                shutil.rmtree(tempdir)

            db.close_old_connections()
            if options['run_once']:
                break
            # Sleep for DELAY seconds
            time.sleep(options['delay'])
