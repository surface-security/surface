import json
import os
import tempfile
import time
import hvac
import tarfile
from docker.errors import APIError
from pathlib import Path
from contextlib import contextmanager

from django.conf import settings
from django.core.management.base import CommandError
from logbasecommand.base import LogBaseCommand

from scanners import models
from scanners import utils
from scanners.inputs.base import query as input_query


class Command(LogBaseCommand):
    help = 'Run a scanner.'

    def add_arguments(self, parser):
        parser.add_argument('-d', '--dry', action='store_true', help='Dry (test) run only, no changes')
        parser.add_argument('-q', '--quiet', action='store_true', help='Do not send notifications')
        parser.add_argument(
            '-c', '--check', action='store_true', help='Check and run scanner only if that is not already running...'
        )
        parser.add_argument(
            '-r', '--rootbox', metavar='ROOTBOX', help='Use ROOTBOX instead of the one assigned to the scanner'
        )
        parser.add_argument('scanner', metavar='SCANNER', help='Scanner name', nargs='?')

    def prepare_input(self, scanner, temp_dir):
        count = 0
        of = temp_dir / 'input.txt'
        _m = input_query
        _inp = scanner.input
        with of.open('w') as fileobj:
            for item in _m(_inp)().generate():
                fileobj.write(item)
                fileobj.write('\n')
                count += 1
        return of, count

    def prepare_input_tar(self, scanner, scanner_args, temp_dir):
        tar_name = temp_dir / 'input.tgz'
        with tarfile.open(tar_name, 'w:gz') as tar:
            _in, inp_count = self.prepare_input(scanner, temp_dir)
            if os.stat(_in).st_size == 0:
                self.log(f'Skipping {scanner.scanner_name} with empty input file')
                return
            scanner_args.append('/input/input.txt')
            tar.add(_in, arcname='input/input.txt')
        return tar_name, inp_count

    def check_running(self, docker, cont_name):
        for c in docker.containers.list(sparse=True):
            if c.attrs.get('Names', [''])[0].lstrip('/').startswith(cont_name):
                self.log_warning('Already running...')
                return True
        return False

    def list_scanners(self):
        self.stdout.write('=== ROOTBOXES ===\n')
        for _r in models.Rootbox.objects.filter(active=True):
            self.stdout.write(str(_r))
        self.stdout.write('\n')
        self.stdout.write('=== SCANNERS ===\n')
        for _r in models.Scanner.objects.all():
            self.stdout.write(str(_r))

    def handle(self, *args, **options):
        if not options['scanner']:
            self.list_scanners()
            return

        try:
            scanner = models.Scanner.objects.get(scanner_name=options['scanner'])
        except models.Scanner.DoesNotExist as e:
            raise CommandError(f'scanner {options["scanner"]} does not exist')

        rootbox = scanner.rootbox
        if options['rootbox']:
            rootbox = models.Rootbox.objects.get(name=options['rootbox'])
        if not rootbox.active:
            raise CommandError(f'{rootbox.name} is not active')

        scanner_args = []
        if scanner.extra_args:
            scanner_args.append(scanner.extra_args)

        env_vars = {}
        if scanner.environment_vars:
            try:
                env_vars = json.loads(scanner.environment_vars)
            except (json.decoder.JSONDecodeError, TypeError):
                self.log_exception(
                    'An error occurred  while parsing the environment variables for %s', scanner.scanner_name
                )

        if scanner.image.vault_secrets:
            client = hvac.Client(url=settings.SCANNERS_VAULT_URL, token=settings.SCANNERS_VAULT_TOKEN)
            vault_secrets = client.read(f'tla_surf/common/scanners/{scanner.scanner_name}')['data']
            env_vars.update(vault_secrets)

        docker = utils.get_docker_client(rootbox.ip, rootbox.dockerd_port, use_tls=rootbox.dockerd_tls)

        cont_name = f'scanner-{ settings.AVZONE }-{ scanner.id }-{ scanner.image.name }-'
        if options['check'] and self.check_running(docker, cont_name):
            return

        # TODO: remove empty output directories? here or in resync_rootbox?

        with temporary_path(prefix='scanner_input_') as temp_dir:
            tar_out = self.prepare_input_tar(scanner, scanner_args, temp_dir)
            if tar_out is None:
                # no input
                return

            image_name = f'{settings.SCANNERS_IMAGE_PREFIX}{ scanner.image.name }'
            try:
                docker.images.pull(image_name, scanner.docker_tag)
            except APIError as e:
                # log warning only, this is optional tag "refresh"
                # registry might be down from time to time (maintenance, etc)
                self.log_warning('failed to pull image: %s', str(e))

            scanner_timestamp = int(time.time())
            c = docker.containers.create(
                f'{image_name}:{scanner.docker_tag}',
                name=f'{cont_name}{ scanner_timestamp }',
                command=' '.join(scanner_args),
                privileged=True,
                environment=env_vars,
                volumes={
                    f'/scanners_{ settings.AVZONE }/output/{ scanner.id }_{ scanner.image.name }/{ scanner_timestamp }/': {
                        'bind': '/output/',
                        'mode': 'rw',
                    }
                },
            )
            with tar_out[0].open('rb') as t:
                c.put_archive('/', t)
            c.start()
            self.log(f'{scanner} started on {rootbox}: {tar_out[1]} input records')


@contextmanager
def temporary_path(**kwargs):
    with tempfile.TemporaryDirectory(**kwargs) as tmpdirname:
        yield Path(tmpdirname)
