import json
from datetime import datetime

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http.response import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.text import capfirst

from core_utils.admin import DefaultModelAdmin
from core_utils.admin_filters import DefaultFilterMixin, DropdownFilter
from dkron.utils import run_async
from scanners import models, utils


class FinalHTTPFilter(DropdownFilter):
    title = "Final HTTP"
    parameter_name = "final_http"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.filter(final_url__startswith="http:")
        elif self.value() == "No":
            return queryset.exclude(final_url__startswith="http:")
        return queryset


class NoLBie1ie2Filter(DropdownFilter):
    title = "No LB or IE1/IE2"
    parameter_name = "no_lb_ie1ie2"

    def lookups(self, request, model_admin):
        return [("Yes", "Yes"), ("No", "No")]

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.filter(record__isnull=False).exclude(
                Q(record__name__startswith="ie1-")
                | Q(record__name__startswith="ie2-")
                | Q(record__name__icontains=".lb.")
                | Q(record__name__icontains=".ie1.")
                | Q(record__name__icontains=".ie2.")
            )
        return queryset


class TypeRecordFilter(DropdownFilter):
    title = "Type Record"
    parameter_name = "type_record"

    def lookups(self, request, model_admin):
        return [("DNS Record", "DNS Record"), ("IP", "IP")]

    def queryset(self, request, queryset):
        if self.value() == "DNS Record":
            return queryset.exclude(record__isnull=True)
        elif self.value() == "IP":
            return queryset.exclude(ip__isnull=True)
        return queryset


class ExitCodeFilter(DropdownFilter):
    title = "Success"
    parameter_name = "success_exit"

    def lookups(self, request, model_admin):
        return [("yes", "Yes"), ("no", "No")]

    def queryset(self, request, queryset):
        val = self.value()
        if val == "yes":
            return queryset.filter(exit_code=0)
        elif val == "no":
            return queryset.filter(exit_code__isnull=False).exclude(exit_code=0)
        else:
            return queryset


@admin.register(models.Rootbox)
class RootboxAdmin(DefaultFilterMixin, DefaultModelAdmin):
    list_display = ("active", "name", "ip", "ssh_user", "ssh_port", "location", "notes")
    list_display_links = ("name",)
    search_fields = ("name", "ip", "ssh_user", "ssh_port", "location", "notes")
    list_filter = ("active", "location")
    actions = ["check_scanners"]

    def check_scanners(self, request, queryset):
        objs = [o.name for o in queryset]
        opts = self.opts
        context = {
            **self.admin_site.each_context(request),
            "module_name": str(opts.verbose_name_plural),
            "preserved_filters": self.get_preserved_filters(request),
            "title": "Running scanners",
            # hack alert: not an object, but works for change_form...
            "original": "Running scanners",
            "opts": opts,
            "has_view_permission": self.has_view_permission(request),
            "output": utils.check_scanners(objs),
        }
        return render(request, "admin/scanners/check_scanners.html", context=context)

    check_scanners.short_description = "Check running scanners"
    check_scanners.allowed_permissions = ("check_scanners",)

    def has_check_scanners_permission(self, request, obj=None):
        return request.user.has_perm("scanners.check_scanners")

    def get_default_filters(self, request):
        return {"active__exact": 1}


@admin.register(models.ScannerImage)
class ScannerImageAdmin(DefaultModelAdmin):
    list_display = ("name", "description", "vault_secrets")
    list_display_links = ("name",)
    search_fields = ("name", "description")


class ScannerAdminForm(forms.ModelForm):
    def clean_environment_vars(self):
        data = self.cleaned_data["environment_vars"]
        if data:
            try:
                json.loads(data)
            except ValueError as e:
                raise forms.ValidationError(f"An error occurred  while parsing the environment variables. {str(e)}")
            return data


@admin.register(models.Scanner)
class ScannerAdmin(DefaultModelAdmin):
    list_display = (
        "id",
        "scanner_name",
        "image",
        "extra_args",
        "input",
        "parser",
        "continous_running",
        "logs_link",
        "notes",
    )
    list_display_links = ("id",)
    search_fields = ("image__name", "scanner_name", "notes")
    list_filter = ("image__name", "rootbox", "continous_running", "input", "parser")
    actions = ["run_scanner"]
    form = ScannerAdminForm

    def run_scanner(self, request, queryset):
        for obj in queryset:
            x = run_async("run_scanner", obj.scanner_name)
            if x is None:
                self.message_user(
                    request, format_html("Scanner {} launching", obj.scanner_name), level=messages.SUCCESS
                )
            else:
                self.message_user(
                    request,
                    format_html(
                        'Scanner {} launching, check log <a href="{}" target="_blank" rel="noopener">here</a>',
                        obj.scanner_name,
                        x[1],
                    ),
                    level=messages.SUCCESS,
                )

    run_scanner.short_description = "Run this scanner..."

    def logs_link(self, obj):
        return format_html(
            '<a href="{}?scanner__id__exact={}"><i class="fas fa-file-alt"></i></a>',
            reverse("admin:scanners_scanlog_changelist"),
            obj.pk,
        )

    logs_link.short_description = "Logs"


@admin.register(models.ScanLog)
class ScanLogAdmin(DefaultModelAdmin):
    list_display = ("id", "name", "scanner", "rootbox", "first_seen", "get_runtime", "get_state", "view_logs")
    list_display_links = ("id",)
    search_fields = ("name", "scanner__scanner_name")
    list_filter = ("scanner", "rootbox", "state", ExitCodeFilter)

    def get_runtime(self, obj):
        return obj.last_seen - obj.first_seen

    get_runtime.short_description = "Runtime"

    def view_logs(self, obj):
        return format_html(
            '<a href="{}"><i class="fas fa-file-alt"></i></a>',
            reverse("admin:scanners_scanlog_output", args=(obj.pk,), current_app=self.admin_site.name),
        )

    view_logs.short_description = "Output"

    def get_state(self, obj):
        state = obj.get_state_display()
        if obj.exit_code is None:
            return state
        if obj.exit_code == 0:
            return format_html('{} <i class="text-success fas fa-check"></i>', state)

        return format_html(
            '{0} <i class="text-danger fas fa-times">({1})</i>',
            obj.get_state_display(),
            obj.exit_code,
        )

    get_state.short_description = "Status"
    get_state.admin_order_field = "state"

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()

        urls.insert(
            0,
            path(
                "<path:object_id>/output/", self.admin_site.admin_view(self.output_view), name="scanners_scanlog_output"
            ),
        )
        return urls

    def _output_view_json(self, request, obj):
        qs = obj.output_lines.order_by("timestamp")
        cursor = None
        if request.GET.get("cursor"):
            try:
                cursor = datetime.fromisoformat(request.GET.get("cursor"))
                qs = qs.filter(timestamp__gt=cursor)
            except (ValueError, TypeError):
                pass
        lines = []
        last_time = None
        for line in qs:
            lines.append((line.timestamp.strftime("%d-%m-%Y %H:%M:%S"), line.line))
            last_time = line.timestamp
        if last_time:
            cursor = last_time
        return JsonResponse(
            {
                "lines": lines,
                "cursor": cursor.isoformat() if cursor is not None else None,
                "state": obj.get_state_display(),
            }
        )

    def output_view(self, request, object_id, extra_context=None):
        # ref: ModelAdmin.history_view
        # First check if the user can see this output.
        model = self.model
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, model._meta, object_id)

        # check that user has permissions on ScanOutput model as well
        if not self.has_view_permission(request) or not (
            request.user.has_perm("scanners.view_scanoutput") or request.user.has_perm("scanners.change_scanoutput")
        ):
            raise PermissionDenied

        if request.GET.get("mode") == "json":
            return self._output_view_json(request, obj)

        output_list = obj.output_lines.order_by("-timestamp")
        raw_mode = request.GET.get("mode") == "raw"
        if raw_mode:
            # return full log in raw plain/text
            return StreamingHttpResponse(
                streaming_content=(f"[{x.timestamp}] {x.line}\n" for x in output_list), content_type="text/plain"
            )
        # otherwise show only last 100 lines
        output_list = output_list[:100]

        # evaluate queryset to make sure secondary queries are made in the template
        output_list = list(output_list)

        opts = model._meta
        context = {
            **self.admin_site.each_context(request),
            "title": "View output: %s" % obj,
            "module_name": str(capfirst(opts.verbose_name_plural)),
            "object_id": object_id,
            "original": obj,
            "opts": opts,
            "output_list": output_list,
            "preserved_filters": self.get_preserved_filters(request),
            "has_view_permission": True,
            "full_mode": len(output_list) < 100,
            **(extra_context or {}),
        }
        request.current_app = self.admin_site.name

        return TemplateResponse(request, "admin/scanners/scanlog_output.html", context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.LiveHost)
class LiveHostAdmin(DefaultModelAdmin):
    list_display = [
        "id",
        "get_host",
        "port",
        "status_code",
        "final_url",
        "third_party",
        "last_seen",
        "get_technologies",
    ]
    list_display_links = ("id",)
    list_filter = (
        "last_seen",
        "port",
        "status_code",
        "third_party",
        "host_content_type",
        "technologies",
        FinalHTTPFilter,
        NoLBie1ie2Filter,
    )
    search_fields = [
        "host__any__name",
        "final_url",
        "redirects",
        "headers",
        "cookies",
        "technologies__name",
        "notes",
    ]
    readonly_fields = [field.name for field in models.LiveHost._meta.fields if field.name not in ("notes",)] + [
        "get_technologies"
    ]
    exclude = ("technologies",)
    list_select_related = ("host_content_type",)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("host", "technologies")

    def get_host(self, obj):
        meta = obj.host_content_type.model_class()._meta
        return format_html(
            '{} (<a href="{}">{}</a>)',
            obj.host,
            reverse(admin_urlname(meta, "change"), args=(obj.host_object_id,)),
            meta.verbose_name,
        )

    get_host.short_description = "Host"
    get_host.admin_order_field = "content_type"

    def get_technologies(self, obj):
        return format_html_join("", '<span class="badge">{}</span>', ((x.name,) for x in obj.technologies.all()))

    get_technologies.short_description = "Technologies"

    def has_add_permission(self, request):
        return False


@admin.register(models.RawResult)
class RawResultAdmin(DefaultFilterMixin, DefaultModelAdmin):
    list_display = ("file_name", "scanner", "rootbox", "last_seen", "notes")
    list_display_links = ("file_name",)
    search_fields = ("raw_results", "file_name")
    list_filter = ("rootbox", "scanner")
    readonly_fields = [field.name for field in models.RawResult._meta.fields if field.name not in ("id")]

    def get_default_filters(self, request):
        return {"active__exact": 1}


@admin.register(models.TechUsedResult)
class TechUsedResultAdmin(DefaultFilterMixin, DefaultModelAdmin):
    list_display = [
        field.name
        for field in models.TechUsedResult._meta.fields
        if field.name not in ("id", "scanner", "rootbox", "notes")
    ]
    list_display_links = ("first_seen",)
    list_filter = (
        "active",
        "rootbox",
        "scanner",
        "first_seen",
        "last_seen",
        "category",
        "application",
        "version",
        "confidence",
    )
    readonly_fields = [field.name for field in models.TechUsedResult._meta.fields if field.name not in ("notes",)]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_default_filters(self, request):
        return {"active__exact": 1}
