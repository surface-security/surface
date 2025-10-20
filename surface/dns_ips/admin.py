import netaddr
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect
from django.http.request import HttpRequest
from django.shortcuts import render
from django.utils.html import format_html_join
from import_export import resources
from import_export.admin import ExportMixin, ImportMixin

from core_utils.admin import DefaultModelAdmin
from core_utils.admin_filters import DefaultFilterMixin, RelatedFieldAjaxListFilter
from core_utils.decorators import admin_link_helper, relatedobj_field

from . import models


@admin.register(models.Source)
class SourceAdmin(DefaultFilterMixin, DefaultModelAdmin):
    list_display = ("name", "active", "last_sync", "notes")
    list_display_links = ("name",)
    search_fields = ("name", "active", "last_sync", "notes")
    list_filter = ("active", "last_sync")

    def get_default_filters(self, request):
        return {"active__exact": 1}


@admin.register(models.Organisation)
class OrganisationAdmin(DefaultFilterMixin, DefaultModelAdmin):
    list_display = [field.name for field in models.Organisation._meta.fields if field.name not in ("id", "source_key")]
    list_display_links = ("name",)
    search_fields = ("name",)
    list_filter = ("active", "owned_by_us", "whitelisted_to_be_scanned")

    def get_default_filters(self, request):
        return {"active__exact": 1}


@admin.register(models.Tag)
class TagAdmin(DefaultModelAdmin):
    list_display = ("name", "notes")
    list_display_links = ("name",)
    search_fields = ("name", "notes")


@admin.register(models.IPRange)
class IPRangeAdmin(DefaultFilterMixin, DefaultModelAdmin):
    list_display = [
        field.name for field in models.IPRange._meta.fields if field.name not in ("id", "range_min", "range_max")
    ]
    list_display_links = ("range",)
    search_fields = ("range", "zone", "datacenter", "description", "notes")
    list_filter = ("source", "active", "zone", "datacenter", "tags")
    exclude = ("range_min", "range_max")

    def get_search_results(self, request, queryset, search_term):
        q, d = super().get_search_results(request, queryset, search_term)
        search_term = search_term.strip()
        if search_term.count(".") == 3:
            try:
                val = netaddr.IPAddress(search_term)
                q |= queryset.filter(range_min__lte=val, range_max__gte=val)
            except Exception:
                # just ignore, it is not an IP
                pass
        return q, d

    def get_queryset(self, request):
        my_model = super().get_queryset(request)
        return my_model

    def get_default_filters(self, request):
        return {"active__exact": 1}


@admin.register(models.IPAddress)
class IPAddress(DefaultFilterMixin, DefaultModelAdmin):
    list_display = (
        "source",
        "active",
        "last_seen",
        "name",
        "organisation",
        "organisation_ip_owner",
        "get_tags",
        "notes",
    )
    list_display_links = ("name",)
    search_fields = ("=name",)
    list_filter = ("source", "active", "tags")
    list_select_related = ("source", "organisation", "organisation_ip_owner")

    slack_display_name = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def get_tags(self, obj):
        return format_html_join("", '<span class="badge">{}</span>', ((x.name,) for x in obj.tags.all()))

    get_tags.short_description = "Tags"

    def get_default_filters(self, request):
        return {"active__exact": 1}


@admin.register(models.DNSDomain)
class DNSDomain(DefaultFilterMixin, DefaultModelAdmin):
    list_display = (
        "source",
        "active",
        "last_seen",
        "name",
        "register_nameservers",
        "registration_date",
        "expire_date",
        "raw_whois",
        "register_registrant_name",
        "register_registrant_organisation",
        "register_registrant_email",
    )
    list_display_links = ("name",)
    search_fields = (
        "name",
        "notes",
        "register_nameservers",
        "registration_date",
        "expire_date",
        "raw_whois",
        "register_management_status",
        "register_dns_managed",
        "register_registrant_name",
        "register_registrant_organisation",
        "register_registrant_address",
        "register_registrant_postcode",
        "register_registrant_city",
        "register_registrant_state",
        "register_registrant_country",
        "register_registrant_phone",
        "register_registrant_fax",
        "register_registrant_email",
        "register_admin_name",
        "register_admin_organisation",
        "register_admin_address",
        "register_admin_postcode",
        "register_admin_city",
        "register_admin_state",
        "register_admin_country",
        "register_admin_phone",
        "register_admin_fax",
        "register_admin_email",
        "register_technical_name",
        "register_technical_organisation",
        "register_technical_address",
        "register_technical_postcode",
        "register_technical_city",
        "register_technical_state",
        "register_technical_country",
        "register_technical_phone",
        "register_technical_fax",
        "register_technical_email",
        "register_account_name",
        "register_email",
        "register_registrar",
        "register_website",
    )
    list_filter = (
        "source",
        "active",
        "registration_date",
        "expire_date",
        "register_registrant_name",
        "register_registrant_organisation",
        "register_registrant_email",
        "register_management_status",
        "register_dns_managed",
    )
    readonly_fields = (
        "registration_date",
        "expire_date",
        "raw_whois",
        "register_management_status",
        "register_dns_managed",
        "register_registrant_name",
        "register_registrant_organisation",
        "register_registrant_address",
        "register_registrant_postcode",
        "register_registrant_city",
        "register_registrant_state",
        "register_registrant_country",
        "register_registrant_phone",
        "register_registrant_fax",
        "register_registrant_email",
        "register_admin_name",
        "register_admin_organisation",
        "register_admin_address",
        "register_admin_postcode",
        "register_admin_city",
        "register_admin_state",
        "register_admin_country",
        "register_admin_phone",
        "register_admin_fax",
        "register_admin_email",
        "register_technical_name",
        "register_technical_organisation",
        "register_technical_address",
        "register_technical_postcode",
        "register_technical_city",
        "register_technical_state",
        "register_technical_country",
        "register_technical_phone",
        "register_technical_fax",
        "register_technical_email",
        "register_account_name",
        "register_email",
        "register_registrar",
        "register_website",
    )

    def get_default_filters(self, request):
        return {"active__exact": 1}


class DNSRecordResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        model = models.DNSRecord
        import_id_fields = ("source", "name")
        fields = ("source", "name")


@admin.register(models.DNSRecord)
class DNSRecordAdmin(DefaultFilterMixin, DefaultModelAdmin):
    resource_class = DNSRecordResource

    list_display = (
        "id",
        "name",
        "source",
        "active",
        "last_seen",
        "tla",
        "domain",
        "get_tags",
    )
    search_fields = ("name", "domain__name", "notes")
    list_filter = (
        ("domain", RelatedFieldAjaxListFilter),
        ("tla__managed_by", RelatedFieldAjaxListFilter),
        ("tla__owned_by", RelatedFieldAjaxListFilter),
        ("tla__director_direct", RelatedFieldAjaxListFilter),
        ("tla__director", RelatedFieldAjaxListFilter),
        ("tla", RelatedFieldAjaxListFilter),
        "source",
        "active",
        "tags",
    )
    list_select_related = ("source", "domain", "tla")

    slack_display_name = True

    actions = ["update_tag_on_selected"]  # override our default

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).prefetch_related("tags")

    def get_tags(self, obj):
        return format_html_join("", '<span class="badge">{}</span>', ((x.name,) for x in obj.tags.all()))

    get_tags.short_description = "Tags"

    def get_default_filters(self, request):
        return {"active__exact": 1}

    def update_tag_on_selected(self, request, queryset):
        if "apply" in request.POST:
            tag = models.Tag.objects.get(pk=request.POST.get("tag", None))
            action = request.POST.get("update", None)

            if action == "add":
                for i in queryset:
                    i.tags.add(tag)
            elif action == "remove":
                for i in queryset:
                    i.tags.remove(tag)
            else:
                self.message_user(request, "Action does not exist")
                return HttpResponseRedirect(request.get_full_path())

            self.message_user(request, f"Updated tags for {queryset.count()} selected items")
            return HttpResponseRedirect(request.get_full_path())

        return render(request, "tag_intermediate.html", context={"items": queryset, "tags": models.Tag.objects.all()})

    update_tag_on_selected.short_description = "Update Tags on selected items"


class DNSRecordValueResource(resources.ModelResource):
    class Meta:
        skip_unchanged = True
        model = models.DNSRecordValue
        import_id_fields = ("source", "name", "rtype", "value")
        fields = ("source", "name", "ttl", "rtype", "value")


@admin.register(models.DNSRecordValue)
class DNSRecordValueAdmin(DefaultFilterMixin, ImportMixin, ExportMixin, DefaultModelAdmin):
    resource_class = DNSRecordValueResource

    list_display = (
        "id",
        admin_link_helper("record"),
        relatedobj_field("record", "source", description="Source"),
        "active",
        "last_seen",
        relatedobj_field("record", "tla", description="TLA"),
        "ttl",
        "rtype",
        "value",
        "get_ips",
    )
    list_display_links = ("id",)
    search_fields = ("record__name", "record__domain__name", "rtype", "value", "ips__name")
    list_filter = (
        ("record", RelatedFieldAjaxListFilter),
        "record__source",
        "active",
        "rtype",
    )
    list_select_related = ("record", "record__tla", "record__source", "record__domain")
    readonly_fields = ("record", "ips")
    slack_display_name = True

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).prefetch_related("ips")

    def get_ips(self, obj):
        return ", ".join([p.name for p in obj.ips.all()])

    get_ips.short_description = "IP List"

    def get_default_filters(self, request):
        return {"active__exact": 1}
