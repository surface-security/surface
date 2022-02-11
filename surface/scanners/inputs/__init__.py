from glob import glob
from os.path import basename, dirname, join

# https://python-notes.curiousefficiency.org/en/latest/python_concepts/import_traps.html
# Import all classes in this directory so that classes with @register_class are registered.
pwd = dirname(__file__)
for x in glob(join(pwd, '*.py')):
    if not x.startswith('_'):
        __import__(f'scanners.inputs.{basename(x)[:-3]}', globals(), locals())
