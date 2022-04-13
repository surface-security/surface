from django.contrib.admin import site
from django.conf import settings


site.site_title = 'Surface'
site.site_url = 'https://github.com/fopina/surface'
site.index_title = 'Home'
site.site_header = ('Surface', settings.SURFACE_VERSION)
