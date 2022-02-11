import os

from scanners import models
from scanners.parsers.base import query
from logbasecommand.base import LogBaseCommand


class ParseException(Exception):
    """error parsing scanner results"""


def parse_results(res_dir, scanner=None, rootbox=None):
    fulldir = os.path.abspath(res_dir)
    _sn = os.path.basename(fulldir)
    _ss = None

    if scanner is None:
        try:
            _sid = int(_sn.split('_')[0])
        except ValueError:
            raise ParseException(f'ERROR-SCANNER: invalid scanner directory: {_sn}')
    else:
        if isinstance(scanner, models.Scanner):
            _ss = scanner
            _sid = scanner.pk
        else:
            _sid = scanner

    if _ss is None:
        try:
            _ss = models.Scanner.objects.get(pk=_sid)
        except models.Scanner.DoesNotExist:
            raise ParseException(f'ERROR-SCANNER: invalid scanner id: {_sid} ({_sn})')

    parse = query(_ss.parser)
    for _st in os.listdir(fulldir):
        _sp = os.path.join(fulldir, _st)
        if not os.listdir(_sp):
            # extra check to avoid useless logging
            continue
        yield f'Processing results for {_ss} - {_sp}'
        try:
            parse(rootbox=rootbox, scanner=_ss, timestamp=_st, filepath=_sp)
        except Exception as ex:
            raise ParseException(f'ERROR-SCANNER: error when parsing {_sn} ({ex})')


class Command(LogBaseCommand):
    help = 'Parse scanner results directory.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            'directory', type=str, help='Directory containing scanner results - subdirectories should be timestamps'
        )

    def handle(self, *args, **options):
        try:
            for m in parse_results(options['directory']):
                self.log(m)
        except ParseException:
            self.log_exception('parser failed')
