import logging
from datetime import datetime
from typing import Any, Optional

import django_filters
from django import forms
from django.contrib import admin, messages
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from jsoneditor.forms import JSONEditor

from core_utils.admin import DefaultModelAdmin
from core_utils.admin_filters import DefaultFilterMixin, DropdownFilter, RelatedFieldAjaxListFilter
from core_utils.utils import admin_reverse
from dkron.utils import run_async
from inventory.models import GitSource
from sca import models
from sca.utils import only_highest_version_dependencies

logger = logging.getLogger(__name__)


class EndOfLifeDependencyBoolFilter(DropdownFilter):
    title = "EoL"
    parameter_name = "eol_filter"
    field = "eol"

    def lookups(self, request, model_admin):
        return [
            ("true", "True"),
            ("false", "False"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "true":
            return queryset.filter(**{f"{self.field}__lte": datetime.now().date()})
        elif value == "false":
            return queryset.filter(**{f"{self.field}__gt": datetime.now().date()})


class LTSFilter(EndOfLifeDependencyBoolFilter):
    title = "LTS"
    parameter_name = "lts_filter"
    field = "lts"


class DiscontinuedFilter(EndOfLifeDependencyBoolFilter):
    title = "Discontinued"
    parameter_name = "lts_filter"
    field = "lts"


class SupportFilter(EndOfLifeDependencyBoolFilter):
    title = "Not Supported"
    parameter_name = "support_filter"
    field = "support"


@admin.register(models.EndOfLifeDependency)
class EndOfLifeDependencyAdmin(DefaultModelAdmin, DefaultFilterMixin, EndOfLifeDependencyBoolFilter):
    list_display = [
        "product",
        "cycle",
        "release_date",
        "latest_release_date",
        "latest_version",
        "is_eol",
        "no_support",
        "is_discontinued",
        "is_lts",
        "link",
    ]
    list_filter = ["product", EndOfLifeDependencyBoolFilter, LTSFilter, DiscontinuedFilter, SupportFilter]
    search_fields = ["product"]


class SCADependencyForm(forms.ModelForm):
    class Meta:
        model = models.SCADependency
        fields = ("dependency_tree", "parent_tree")

    # Custom field
    dependency_tree = forms.JSONField(
        widget=JSONEditor(attrs={"style": "background-color: white !important;"}), label="Dependency Tree"
    )
    parent_tree = forms.JSONField(
        widget=JSONEditor(attrs={"style": "background-color: white !important;"}), label="Parent Tree"
    )

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance", None)
        if instance:
            kwargs["initial"] = {
                "dependency_tree": instance.dependency_tree,
                "parent_tree": instance.parent_tree,
            }
        super().__init__(*args, **kwargs)


@admin.register(models.SCADependency)
class SCADependencyAdmin(DefaultModelAdmin):
    form = SCADependencyForm
    list_display = [
        "purl",
        "get_git_source",
        "get_dependencies",
        "name",
        "version",
        "dependency_type",
    ]
    list_filter = [
        "dependency_type",
        "name",
        "git_source__repo_url",
        "git_source__apps__tla",
        "is_public",
        "is_project",
    ]
    search_fields = ["name", "purl", "depends_on__name", "depends_on__purl"]
    readonly_fields = [field.name for field in models.SCADependency._meta.fields] + [
        "depends_on",
        "git_source",
    ]

    list_select_related = ["git_source"]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("depends_on", "git_source__apps")

    @admin.display(description="Repository")
    def get_git_source(self, obj):
        if obj.git_source:
            return format_html(
                f'<a target="_blank" href="/tlaconfig/gitsource/{obj.git_source.pk}">{obj.git_source.repo_url}</a>'
            )

    @admin.display(description="Depends On")
    def get_dependencies(self, obj):
        links = "<br>".join(
            [
                f'<a target="_blank" href="/sca/scadependency/?purl={dep.purl}">{dep.purl}</a>'
                for dep in obj.depends_on.only("purl")
            ]
        )
        return format_html(links)

    fieldsets = (
        (
            "General Info",
            {
                "classes": ["tab"],
                "fields": (
                    "purl",
                    "name",
                    "version",
                    "dependency_type",
                    "git_source",
                ),
            },
        ),
        (
            "Dependency Tree",
            {
                "classes": ["tab"],
                "fields": ("dependency_tree",),
            },
        ),
        (
            "Parent Tree",
            {
                "classes": ["tab"],
                "fields": ("parent_tree",),
            },
        ),
    )


class SCAFindingFilter(django_filters.FilterSet):
    dependency__purl = django_filters.CharFilter(lookup_expr="icontains", label="Dependency")

    FIXED_IN_CHOICES = (
        ("true", "True"),
        ("false", "False"),
    )

    fixed_in = django_filters.ChoiceFilter(choices=FIXED_IN_CHOICES, method="filter_fixed_in", label="Fixable")

    class Meta:
        model = models.SCAFinding
        fields = ["severity", "state", "dependency__purl", "finding_type"]

    def filter_fixed_in(self, queryset, name, value):
        if value == "true":
            return queryset.exclude(fixed_in="")
        elif value == "false":
            return queryset.filter(fixed_in="")
        return queryset


class SCADependencyFilter(django_filters.FilterSet):
    purl = django_filters.CharFilter(lookup_expr="icontains", label="Dependency", method="filter_purl")
    show_vulnerable = django_filters.BooleanFilter(
        method="filter_vulnerable", widget=django_filters.widgets.BooleanWidget(attrs={"data-toggle": "toggle"})
    )

    IS_PUBLIC_CHOICES = (
        ("true", "True"),
        ("false", "False"),
    )

    is_public = django_filters.ChoiceFilter(choices=IS_PUBLIC_CHOICES, method="filter_is_public", label="Is Public")

    def filter_is_public(self, queryset, name, value):
        if value == "true":
            queryset = queryset.filter(is_public=True)
        elif value == "false":
            queryset = queryset.filter(is_public=False)
        return queryset

    class Meta:
        model = models.SCADependency
        fields = ["purl", "show_vulnerable", "is_public"]

    def filter_purl(self, queryset, name, value):
        return queryset.filter(Q(purl__icontains=value) | Q(depends_on__purl__icontains=value))

    def filter_vulnerable(self, queryset, name, value):
        if value:
            return queryset.annotate(vuln_count=Count("scafinding")).filter(vuln_count__gt=0)
        return queryset


@admin.register(models.SCAProject)
class SCAProjectAdmin(DefaultModelAdmin):
    list_display = ["purl", "get_vulns", "get_git_source", "get_sbom_link", "name", "last_scan", "created_at"]
    list_filter = [
        "name",
        "git_source",
        ("git_source__apps", RelatedFieldAjaxListFilter),
    ]
    search_fields = ["name", "purl", "depends_on__name", "depends_on__purl", "git_source__repo_url"]

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        self.change_form_template = "views/dependencies.html"

        obj = self.get_object(request, object_id)

        if not obj:
            obj = models.SCADependency.objects.get(pk=int(object_id))

        extra_context["current_object"] = obj
        extra_context["vulnerabilities"] = []
        extra_context["dependencies"] = []
        extra_context["show_vulnerable"] = "show_vulnerable" in request.GET

        if request.GET.get("view") == "vulnerabilities":
            self.change_form_template = "views/vulnerabilities.html"
            extra_context["vuln_colors"] = {
                models.SCAFinding.Severity.CRITICAL: "red",
                models.SCAFinding.Severity.HIGH: "orange",
                models.SCAFinding.Severity.MEDIUM: "yellow",
                models.SCAFinding.Severity.LOW: "blue",
                models.SCAFinding.Severity.INFORMATIVE: "green",
            }

            vulnerabilities = self.get_vulnerabilities(obj)
            # set fixed_in as True by default if not passed in the request
            if "fixed_in" not in request.GET:
                request.GET = request.GET.copy()
                request.GET["fixed_in"] = "true"
            extra_context["vulns_filter"] = SCAFindingFilter(request.GET, queryset=vulnerabilities)

        if request.method == "POST":
            git_source = obj.git_source if hasattr(obj, "git_source") else None
            if request.POST.get("action") == "run_renovate_dependencies":
                vulnerabilities = self.get_vulnerabilities(obj)
                dependencies = [vuln.dependency.purl for vuln in vulnerabilities]
                self.renovate(request, git_source, dependencies)
                return HttpResponseRedirect(request.get_full_path())

            elif request.POST.get("action") == "run_renovate_dependencies_no_deps":
                self.renovate(request, git_source)
                return HttpResponseRedirect(request.get_full_path())

            elif request.POST.get("action") == "run_renovate_dependency":
                dependency_id = request.POST.get("dependency_id")
                dependency = models.SCADependency.objects.get(pk=dependency_id).purl
                self.renovate(request, git_source, dependency)
                return HttpResponseRedirect(request.get_full_path())

            return HttpResponseRedirect(request.get_full_path())
        else:
            # Get only the highest version dependencies as those should be the ones actually installed
            project_deps = only_highest_version_dependencies(obj.dependencies)

            dependencies = (
                models.SCADependency.objects.filter(purl__in=project_deps)
                .prefetch_related("depends_on", "git_source__apps")
                .exclude(purl=obj.purl)
            )

            filtered_dependencies = []
            for dep in SCADependencyFilter(request.GET, queryset=dependencies).qs:
                dep_dict = model_to_dict(dep)
                dep_dict["created_at"] = dep.created_at
                dep_dict["vulns_counters"] = dep.get_vulns_counter(obj)
                filtered_dependencies.append(dep_dict)

            extra_context["deps_filter"] = SCADependencyFilter(request.GET, queryset=dependencies).form
            extra_context["dependencies"] = filtered_dependencies

        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def get_vulnerabilities(self, obj):
        """Retrieve and filter vulnerabilities."""
        suppressed_findings = models.SuppressedSCAFinding.objects.filter(
            Q(sca_project=obj) | Q(sca_project__isnull=True)
        ).values_list("vuln_id", flat=True)
        vulnerabilities = (
            models.SCAFinding.objects.filter(
                dependency__purl__in=obj.dependencies,
                state__in=(models.SCAFinding.State.NEW, models.SCAFinding.State.OPEN),
            )
            .prefetch_related("dependency")
            .exclude(vuln_id__in=suppressed_findings)
        )

        highest_version_vulns_purls = only_highest_version_dependencies(
            vulnerabilities.values_list("dependency__purl", flat=True).distinct()
        )

        return vulnerabilities.filter(dependency__purl__in=highest_version_vulns_purls)

    def renovate(self, request, git_source: Optional[GitSource], dependencies=None):
        """Helper method to process sources for renovation."""
        if not git_source:
            messages.error(request, "No sources found for the project.")
            return

        try:
            if dependencies:
                run_async("renovate_dependencies", git_source.repo_url, dependencies=dependencies)
            else:
                run_async("renovate_dependencies", git_source.repo_url)
            messages.success(
                request,
                f"Renovate was just called for {git_source.repo_url}. A new Merge/Pull Request will be created.",
            )
        except Exception as e:
            logger.exception(f"Failed to initiate renovation for {git_source.repo_url}: {str(e)}")
            messages.error(request, f"Failed to initiate renovation for {git_source.repo_url}: {str(e)}")

    @admin.display(description="Repository")
    def get_git_source(self, obj):
        if obj.git_source:
            return format_html(
                f'<a target="_blank" href="/tlaconfig/gitsource/{obj.git_source.pk}">{obj.git_source.repo_url}</a>'
            )

    @admin.display(description="SBOM")
    def get_sbom_link(self, obj):
        if obj.sbom_uuid:
            return format_html(
                '<a href="{}" target="_blank">Download sbom json</a>',
                reverse("sca:download_sbom_as_json", args=[obj.sbom_uuid, obj.name]),
            )

    @admin.display(description="Vulnerabilities")
    def get_vulns(self, obj):
        vulns_counter = models.SCAFindingCounter.objects.filter(dependency=obj).first()

        severity_mapping = {
            models.SCAFinding.Severity.CRITICAL: {
                "counter": vulns_counter.critical if vulns_counter else 0,
                "color": "red",
                "severity": models.SCAFinding.Severity.CRITICAL.label.capitalize(),
            },
            models.SCAFinding.Severity.HIGH: {
                "counter": vulns_counter.high if vulns_counter else 0,
                "color": "orange",
                "severity": models.SCAFinding.Severity.HIGH.label.capitalize(),
            },
            models.SCAFinding.Severity.MEDIUM: {
                "counter": vulns_counter.medium if vulns_counter else 0,
                "color": "yellow",
                "severity": models.SCAFinding.Severity.MEDIUM.label.capitalize(),
            },
            models.SCAFinding.Severity.LOW: {
                "counter": vulns_counter.low if vulns_counter else 0,
                "color": "blue",
                "severity": models.SCAFinding.Severity.LOW.label.capitalize(),
            },
            "eol": {"counter": vulns_counter.eol if vulns_counter else 0, "color": "black", "severity": "End of Life"},
        }

        formatted_items = [
            '<a target="_blank" href="/sca/scaproject/{pk}/change/?view=vulnerabilities&severity={criticality}&finding_type={finding_type}" '
            'title="{counter} {severity}" class="ui {color} circular label">{counter}</a>'.format(
                pk=obj.pk,
                counter=vuln["counter"],
                severity=vuln["severity"],
                color=vuln["color"],
                criticality=criticality if criticality != "eol" else None,
                finding_type=models.SCAFinding.FindingType.VULN
                if criticality != "eol"
                else models.SCAFinding.FindingType.EOL,
            )
            for criticality, vuln in severity_mapping.items()
        ]

        return format_html(
            '<div style="display: flex; gap: 4px; flex-wrap: nowrap;">{}</div>',
            mark_safe("".join(formatted_items)),
        )

    def get_queryset(self, request):
        if request.resolver_match.view_name == "admin:sca_scaproject_change":
            return super().get_queryset(request).prefetch_related("depends_on")
        return (
            super()
            .get_queryset(request)
            .filter(is_project=True)
            .prefetch_related("depends_on", "git_source", "git_source__apps")
        )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def lookup_allowed(self, lookup, value):
        if lookup == "git_source__apps__tla":  # not covered by list_filter
            return True
        return super().lookup_allowed(lookup, value)


@admin.register(models.SCAFinding)
class SCAFindingAdmin(DefaultModelAdmin):
    list_display = [
        "vuln_id",
        # "truncated_aliases",
        "title",
        "severity",
        "state",
        "published",
        # "truncated_fixed_in",
        "ecosystem",
        "finding_type",
        "first_seen",
        "last_seen_date",
    ]

    # search_fields = ["vuln_id", "ecosystem", "title", "summary", "aliases"]
    # list_select_related = ["dependency"]

    # @admin.display(description="Aliases")
    # def truncated_aliases(self, obj):
    #     return truncatechars(obj.aliases, 50)

    # @admin.display(description="Fixed In")
    # def truncated_fixed_in(self, obj):
    #     return truncatechars(obj.fixed_in, 50)

    # def suppress_finding(self, request, obj):
    #     return redirect(
    #         admin_reverse(
    #             models.SuppressedSCAFinding,
    #             "add",
    #             request=request,
    #             query_kwargs={"dependency": obj.dependency_id, "vuln_id": obj.vuln_id},
    #         )
    #     )

    # suppress_finding.label = "Suppress Finding"
    # suppress_finding.attrs = {"class": "btn btn-round ml-auto btn-warning"}
    # suppress_finding.short_description = "This button will Suppress this finding"


@admin.register(models.SuppressedSCAFinding)
class SuppressedSCAFindingAdmin(DefaultModelAdmin):
    list_display = [
        "vuln_id",
        "get_dependency",
        "suppress_reason",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ]
    list_filter = [
        "vuln_id",
        ("dependency", RelatedFieldAjaxListFilter),
        ("sca_project", RelatedFieldAjaxListFilter),
    ]
    search_fields = [
        "vuln_id",
        "dependency__purl",
        "sca_project",
    ]
    list_select_related = ["dependency", "created_by", "updated_by"]
    readonly_fields = ["created_by", "updated_by"]

    @admin.display(description="Dependency")
    def get_dependency(self, obj):
        return format_html(
            '<a target="_blank" href="{}">{}</a>',
            admin_reverse(obj.dependency, "changelist", relative=True, query_kwargs={"purl": obj.dependency.purl}),
            obj.dependency.purl,
        )

    @admin.display(description="SCA Project")
    def get_sca_project(self, obj):
        if obj.sca_project:
            return format_html(
                '<a target="_blank" href="{}">{}</a>',
                admin_reverse(
                    obj.sca_project,
                    "changelist",
                    relative=True,
                    query_kwargs={"name": obj.sca_project.name},
                ),
                obj.sca_project.name,
            )
        return None

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)

        # Retrieve URL parameters
        dependency = request.GET.get("dependency_id")
        vuln_id = request.GET.get("vuln_id")

        # Pre-fill the form fields if data is available
        if dependency:
            try:
                # Assuming Dependency is the related model
                dependency_instance = models.SCADependency.objects.get(pk=int(dependency))
                initial["dependency"] = dependency_instance
            except models.SCADependency.DoesNotExist:
                pass  # Handle the case when the Dependency does not exist

        if vuln_id:
            initial["vuln_id"] = vuln_id

        return initial

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Only for new objects
            dependency_id = request.GET.get("dependency_id")
            project_id = request.GET.get("project_id")
            if dependency_id and project_id:
                form.base_fields["vuln_id"].initial = request.GET.get("vuln_id")
                form.base_fields["vuln_id"].disabled = True
                try:
                    dependency_instance = models.SCADependency.objects.get(pk=int(dependency_id))
                    project_instance = models.SCAProject.objects.get(pk=int(project_id))
                    form.base_fields["dependency"].queryset = models.SCADependency.objects.filter(
                        pk=dependency_instance.pk
                    )
                    form.base_fields["sca_project"].queryset = models.SCAProject.objects.filter(pk=project_instance.pk)
                    form.base_fields["dependency"].initial = dependency_instance
                    form.base_fields["dependency"].disabled = True
                    form.base_fields["dependency"].widget.can_add_related = False
                    form.base_fields["dependency"].widget.can_change_related = False
                    form.base_fields["dependency"].widget.can_delete_related = False
                    form.base_fields["sca_project"].initial = project_instance
                    form.base_fields["sca_project"].disabled = True
                    form.base_fields["sca_project"].widget.can_add_related = False
                    form.base_fields["sca_project"].widget.can_change_related = False
                    form.base_fields["sca_project"].widget.can_delete_related = False
                except (models.SCADependency.DoesNotExist, models.SCAProject.DoesNotExist):
                    pass  # Handle the case when the Dependency does not exist
        return form

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        if not obj.created_by:
            obj.created_by = request.user
        # Close SCA Finding
        if not obj.sca_project:
            closed_sca_findings = models.SCAFinding.objects.filter(
                dependency=obj.dependency,
                vuln_id=obj.vuln_id,
                state__in=(models.SCAFinding.State.NEW, models.SCAFinding.State.OPEN),
            ).update(state=models.SCAFinding.State.CLOSED)
            if closed_sca_findings:
                messages.success(
                    request,
                    format_html(
                        "{} Findings Closed!",
                        closed_sca_findings,
                    ),
                )
        else:
            messages.success(
                request,
                format_html(
                    "{} Suppressed!",
                    obj.vuln_id,
                ),
            )

        return super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset: QuerySet[Any]) -> None:
        reopened_sca_findings = 0
        for obj in queryset:
            if not obj.sca_project:
                reopened_sca_findings = models.SCAFinding.objects.filter(
                    dependency=obj.dependency, vuln_id=obj.vuln_id, state=models.SCAFinding.State.CLOSED
                ).update(state=models.SCAFinding.State.OPEN)

        if reopened_sca_findings:
            messages.success(
                request,
                format_html(
                    "{} Findings Re-Opened!",
                    reopened_sca_findings,
                ),
            )
        return super().delete_queryset(request, queryset)


@admin.register(models.SCAFindingCounter)
class SCAFindingCounterAdmin(DefaultModelAdmin):
    list_display = ["get_purl", "critical", "high", "medium", "low", "eol", "last_sync"]
    list_filter = ["dependency__purl"]
    list_select_related = ["dependency"]

    @admin.display(description="Dependency")
    def get_purl(self, obj):
        return obj.dependency.purl

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
