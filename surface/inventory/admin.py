from django.contrib import admin
from django.contrib.admin.decorators import register
from django.template.defaultfilters import truncatechars
from django.utils.html import format_html

from theme.filters import RelatedFieldAjaxListFilter

from . import models


@register(models.Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "tla",
        "managed_by",
        "owned_by",
        "director",
        "director_direct",
        "dev_lead",
    ]
    list_filter = (
        ("dev_lead", RelatedFieldAjaxListFilter),
        ("managed_by", RelatedFieldAjaxListFilter),
        ("owned_by", RelatedFieldAjaxListFilter),
        ("director", RelatedFieldAjaxListFilter),
        ("director_direct", RelatedFieldAjaxListFilter),
    )

    search_fields = ("tla",)

    list_select_related = (
        "dev_lead",
        "managed_by",
        "owned_by",
        "director",
        "director_direct",
    )


@admin.register(models.GitSource)
class GitSourceAdmin(admin.ModelAdmin):
    filter_vertical = ("apps",)
    list_display = (
        "id",
        "get_apps",
        "get_link",
        "branch",
        "active",
        "manually_inserted",
        "created_at",
        "updated_at",
    )
    search_fields = ("apps__tla", "type", "repo_url")
    list_filter = (
        ("apps", RelatedFieldAjaxListFilter),
        "active",
        "manually_inserted",
    )

    @admin.display(description="Applications")
    def get_apps(self, obj):
        return truncatechars(", ".join(x.tla for x in obj.apps.all()), 50)

    @admin.display(description="Repo")
    def get_link(self, obj):
        if obj.repo_url:
            return format_html(
                '<a href="{url}" target="_blank">{url}</a>', url=obj.repo_url
            )  # nosec - intencional use in order to create admin links
        return ""

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("apps")

    def lookup_allowed(self, lookup, value):
        if lookup == "apps__tla":  # not covered by list_filter
            return True
        return super().lookup_allowed(lookup, value)
