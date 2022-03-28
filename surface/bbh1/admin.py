from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from . import models

@admin.register(models.Scope)
class Scope(SimpleHistoryAdmin):
    list_display = ['name', 'get_link', 'monitor', 'torify', 'disabled', 'big_scope']
    search_fields = ['name', 'description', 'link', 'scope_domains_in', 'scope_domains_out']
    list_filter = ['monitor', 'torify', 'disabled']

    def get_link(self, obj):
        if obj.link:
            return format_html('<a href="{}" target=_blank>{}</a>', obj.link, obj.link)
    get_link.short_description = 'Link'
    get_link.admin_order_field = 'link'
