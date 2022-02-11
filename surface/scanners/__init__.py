from django.utils.module_loading import autodiscover_modules


def autodiscover():
    autodiscover_modules('scanners')
