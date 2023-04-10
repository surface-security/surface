from django.contrib.admin import site
from django.contrib.auth import admin
from impersonate.admin import impersonate_action

admin.UserAdmin.actions.append(impersonate_action)

site.site_title = 'Surface'
site.site_url = 'https://github.com/surface-security/surface'
site.index_title = 'Home'
