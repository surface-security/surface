from time import sleep

from django import db
from django.core.management import call_command
from django.conf import settings

from database_locks import locked
from scanners import models, utils
from scanners.management.commands import run_scanner
from logbasecommand.base import LogBaseCommand


@locked
class Command(LogBaseCommand):
    help = 'Run scanners continuously.'

    def add_arguments(self, parser):
        parser.add_argument('--delay', default=60, type=int, help='Check (and re-run) interval (in seconds)')
        parser.add_argument(
            '-r', '--rootbox', metavar='ROOTBOX', help='only manage scanners attached to this rootbox (default is all)'
        )

    def handle_loop(self, rootbox_name=None):
        running_scanners = {}
        qs = models.Scanner.objects.filter(continous_running=True).select_related('rootbox', 'image').all()
        if rootbox_name:
            qs = qs.filter(rootbox__name=rootbox_name)

        for scanner in qs:
            # do not try to start scanners on disabled rootboxes
            if not scanner.rootbox.active:
                self.log_error(
                    '%s cannot be started as rootbox %s is not active', scanner.scanner_name, scanner.rootbox.name
                )
                continue
            # check if scanner is already running on that specific rootbox
            # check here instead of "run_scanner -c" command to avoid "docker ps" multiple times on the same box
            rootbox = scanner.rootbox.name
            if rootbox not in running_scanners:
                running_scanners[rootbox] = list(utils.check_scanners_in_box(scanner.rootbox))
            cont_name = f'scanner-{settings.AVZONE}-{scanner.id}-{scanner.image.name}-'
            for _c, _ in running_scanners[rootbox]:
                if _c.startswith(cont_name):
                    self.log_debug('%s already running', scanner.scanner_name)
                    break
            else:
                call_command(run_scanner.Command(), scanner)

    def handle(self, *args, **options):
        self.stdout.write('Running scanners continuously...\n')

        while True:
            db.close_old_connections()
            self.handle_loop(rootbox_name=options['rootbox'])
            db.close_old_connections()
            sleep(options['delay'])
