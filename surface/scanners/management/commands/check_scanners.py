import json

from logbasecommand.base import LogBaseCommand
from scanners import utils


class Command(LogBaseCommand):
    help = 'Check running scanners in the rootbox(es).'

    def add_arguments(self, parser):
        parser.add_argument('-r', '--rootbox', help='Check only ROOTBOX')

    def handle(self, *args, **options):
        out = utils.check_scanners([options['rootbox']] if options['rootbox'] else None)

        for _ob, _oo in out:
            self.log(f'## BOX: {_ob}')
            self.log(json.dumps(_oo, indent=4))
            self.log('')
