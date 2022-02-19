from docker.errors import APIError

from django.conf import settings

from scanners import models
from scanners import utils
from logbasecommand.base import LogBaseCommand


class Command(LogBaseCommand):
    help = 'Launch  a playbook that sync scanner data to the rootbox.'

    def add_arguments(self, parser):
        parser.add_argument(
            'rootbox',
            nargs='+',
            help='Use ROOTBOX instead of the one assigned to the scanner',
        )
        parser.add_argument(
            '--recreate', action='store_true', help='Delete existing container, if any, and start a new one'
        )

    def handle(self, *args, **options):
        # validate that all rootboxes exist before processing
        boxes = [models.Rootbox.objects.get(name=rootbox) for rootbox in set(options['rootbox'])]
        container_name = f'squid-{settings.AVZONE}'

        def _doit(docker, rootbox):
            c = docker.containers.create(
                f'{settings.SCANNERS_PROXY_IMAGE}:{settings.SCANNERS_PROXY_IMAGE_TAG}',
                name=container_name,
                environment={
                    'SCANNER_USERNAME': settings.SCANNERS_PROXY_USERNAME,
                    'SCANNER_PASSWORD': settings.SCANNERS_PROXY_PASSWORD,
                },
                ports={3128: 1080},
            )
            c.start()
            self.log(f'Started {c} on {rootbox}')
            return c

        for rootbox in boxes:
            docker = utils.get_docker_client(rootbox.ip, rootbox.dockerd_port, use_tls=rootbox.dockerd_tls)
            try:
                docker.images.pull(settings.SCANNERS_PROXY_IMAGE, settings.SCANNERS_PROXY_IMAGE_TAG)
            except APIError as e:
                # log warning only, this is optional tag "refresh"
                # registry might be down from time to time (maintenance, etc)
                self.log_warning('failed to pull image: %s', str(e))

            try:
                _doit(docker, rootbox)
            except APIError as e:
                if e.status_code == 409 and ' is already in use by container ' in e.explanation:
                    self.log_warning(f'already running in {rootbox.name}')
                    if options['recreate']:
                        # no need to call API to get container if we know its name
                        from docker.models.containers import Container

                        c = Container(client=docker, attrs={'Id': container_name})
                        c.remove()
                        _doit(docker, rootbox)
                else:
                    raise
