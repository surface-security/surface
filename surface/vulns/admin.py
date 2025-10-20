from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from core_utils.admin import DefaultModelAdmin
from core_utils.decorators import admin_link
from vulns import models


@admin.register(models.Finding)
class FindingAdmin(DefaultModelAdmin):
    search_fields = ["id", "title", "summary"]
    list_display = [
        "id",
        "title",
        "severity",
        "summary",
        "state",
        "get_tla_link",
        "get_content_source",
    ]

    list_select_related = ["content_source"]

    list_filter = [
        "severity",
        "state",
    ]

    @admin_link("application", "Application")
    def get_tla_link(self, app):
        return str(app)

    def get_content_source(self, obj):
        meta = obj.content_source.model_class()._meta
        return format_html(
            '<a href="{}">{}</a>',
            reverse(f"admin:{meta.app_label}_{meta.model_name}_change", args=(obj.pk,)),
            f"{meta.app_label}: {meta.verbose_name}",
        )

    get_content_source.short_description = "Content Source"
    get_content_source.admin_order_field = "content_source"

    def has_delete_permission(self, request, obj=None):
        # check children Admin model for ALLOW_DELETE!
        if obj is None:
            return False
        k = obj.content_source.model_class()
        ak = self.admin_site._registry.get(k)
        if ak is None or not ak.ALLOW_DELETE:
            return False
        return admin.ModelAdmin.has_delete_permission(self, request, obj)
