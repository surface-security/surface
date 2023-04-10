from django.contrib import admin
from django.contrib.admin.decorators import register
from django.urls import reverse
from django.utils.html import format_html

from . import models


@register(models.Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    empty for now
    """


@admin.register(models.Finding)
class FindingAdmin(admin.ModelAdmin):
    list_select_related = ['content_source']

    def get_list_display(self, request):
        l = super().get_list_display(request).copy()
        l.insert(1, 'get_content_source')
        return l

    def get_readonly_fields(self, request, obj=None):
        l = super().get_readonly_fields(request, obj=obj).copy()
        l.insert(1, 'get_content_source')
        return l

    def get_content_source(self, obj):
        meta = obj.content_source.model_class()._meta
        return format_html(
            '<a href="{}">{}</a>',
            reverse(f'admin:{meta.app_label}_{meta.model_name}_change', args=(obj.pk,)),
            f'{meta.app_label}: {meta.verbose_name}',
        )

    get_content_source.short_description = 'Content Source'
    get_content_source.admin_order_field = 'content_source'
