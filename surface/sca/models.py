from datetime import datetime
from enum import Enum
from typing import Union

from django.db import models
from django.db.models import Case, Count, Q, When
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core_utils.decorators import lru_cache_time
from sca.utils import cleanup_tree, cvss_to_score, invert_dict, only_highest_version_dependencies
from vulns import models as vuln_models


class EndOfLifeDependency(models.Model):
    product = models.CharField(max_length=255)
    cycle = models.CharField(max_length=255)
    release_date = models.DateField(help_text="Release Date for the first release in this cycle")
    latest_release_date = models.DateField(
        null=True, blank=True, help_text="Release Date for the latest release in this cycle"
    )
    eol = models.DateField(null=True, blank=True, help_text="End of Life Date for this release cycle")
    latest_version = models.CharField(max_length=255, help_text="Latest release in this cycle")
    link = models.URLField(
        max_length=255, default="", blank=True, help_text="Link to changelog for the latest release, if available"
    )
    lts = models.DateField(null=True, blank=True, help_text="Whether this release cycle has long-term-support (LTS)")
    support = models.DateField(null=True, blank=True, help_text="Whether this release cycle has active support")
    discontinued = models.DateField(null=True, blank=True, help_text="Whether this cycle is now discontinued")

    def is_eol(self):
        return self.eol <= datetime.now().date()

    is_eol.boolean = True

    def is_lts(self):
        return self.lts <= datetime.now().date()

    is_lts.boolean = True

    def no_support(self):
        return self.support <= datetime.now().date()

    no_support.boolean = True

    def is_discontinued(self):
        return self.discontinued <= datetime.now().date()

    is_discontinued.boolean = True

    class Meta:
        unique_together = [("product", "cycle")]
        verbose_name = "End of Life Dependency (SCA)"
        verbose_name_plural = "End of Life Dependencies (SCA)"


DependencyTree = Union[list[str], dict[str, "DependencyTree"]]


class SCADependency(models.Model):
    purl = models.CharField(max_length=255, unique=True)
    dependency_type = models.CharField(max_length=21)
    name = models.CharField(max_length=128)
    version = models.CharField(max_length=128)
    git_source = models.ForeignKey("inventory.GitSource", null=True, on_delete=models.SET_NULL)
    depends_on = models.ManyToManyField("self", symmetrical=False)
    is_project = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scan = models.DateTimeField()
    sbom_uuid = models.CharField(max_length=255, default=None, null=True)

    @staticmethod
    def get_dependencies_recursively(
        dependency: "SCADependency", parsed_deps: set[int], results: dict[int, DependencyTree]
    ) -> DependencyTree:
        if dependency.pk in results:
            return results[dependency.pk]

        if dependency.pk in parsed_deps:  # seen node, return direct deps only
            dependencies = []
            for dep in dependency.depends_on.only("purl"):
                dependencies.append(dep.purl)
            results[dependency.pk] = dependencies
            return dependencies

        parsed_deps.add(dependency.pk)

        dependencies = {}
        for dep in dependency.depends_on.only("purl", "depends_on").prefetch_related("depends_on"):
            dependencies[dep.purl] = SCADependency.get_dependencies_recursively(dep, parsed_deps, results)

        results[dependency.pk] = dependencies
        return dependencies

    @property
    def dependency_tree(self):
        dependencies = {self.purl: SCADependency.get_dependencies_recursively(self, set(), {})}
        return cleanup_tree(dependencies)

    @staticmethod
    def get_parents_recursively(
        dependency: "SCADependency", parsed_parents: set
    ) -> tuple[DependencyTree, set["SCADependency"]]:
        parents = {}
        projects = set()

        for par in dependency.scadependency_set.only("purl", "depends_on", "git_source").prefetch_related(
            "scadependency_set", "git_source"
        ):
            if par.purl not in parsed_parents:
                parsed_parents.add(par.purl)
                parents[par.purl], parent_projects = SCADependency.get_parents_recursively(par, parsed_parents)
                projects.update(parent_projects)
                if par.is_project:
                    projects.add(par)

        return parents, projects

    @property
    def parent_tree(self):
        parents, _ = SCADependency.get_parents_recursively(self, set())
        parent_dict = {self.purl: parents}
        return cleanup_tree(invert_dict(parent_dict))

    @property
    def projects(self):
        parsed_parents = set()
        _, parent_projects = SCADependency.get_parents_recursively(self, parsed_parents)
        return parent_projects

    def get_vulns_counter(self, project):
        suppressed_findings = (
            SuppressedSCAFinding.objects.filter(dependency=self)
            .filter(Q(sca_project__isnull=True) | Q(sca_project=project))
            .values_list("vuln_id", flat=True)
        )

        findings = (
            SCAFinding.objects.filter(dependency=self)
            .select_related("dependency")
            .values("severity", "finding_type")
            .annotate(count=Count("severity"), eol=Count(Case(When(finding_type=1, then=1))))
            .order_by("-severity")
        ).exclude(vuln_id__in=suppressed_findings)
        return {item["severity"]: {"count": item["count"], "eol": item["eol"]} for item in findings}

    @staticmethod
    @lru_cache_time(3600)
    def get_dependencies(root_dependency: "SCADependency") -> list:
        dependencies = set()
        stack = [root_dependency]

        # Prefetch all necessary data before starting the loop
        root_dependency.depends_on.only("purl", "depends_on").prefetch_related("depends_on")

        while stack:
            current_dep = stack.pop()

            # Add the current dependency's purl to the set of dependencies
            dependencies.add(str(current_dep.purl))

            # Iterate over the dependencies of the current dependency
            for dep in current_dep.depends_on.all():
                if str(dep.purl) not in dependencies:
                    stack.append(dep)

        return list(dependencies)

    def update_vulnerability_counters(self) -> "SCAFindingCounter":
        project_suppressed_findings = SuppressedSCAFinding.objects.filter(sca_project=self)
        severity_counters = (
            SCAFinding.objects.filter(
                (Q(fixed_in__gt="") | Q(finding_type=SCAFinding.FindingType.EOL)),
                dependency__purl__in=self.dependencies,
                state__in=(SCAFinding.State.NEW, SCAFinding.State.OPEN),
            )
            .exclude(vuln_id__in=project_suppressed_findings.values_list("vuln_id", flat=True))
            .prefetch_related("dependency")
            .values("severity")
            .annotate(
                count_eol=Count(Case(When(severity__isnull=True, then=1))),
                count=Count("severity"),
            )
        )

        severities = {severity.label.lower(): 0 for severity in SCAFinding.Severity}
        severities["eol"] = 0

        highest_version_vulns_purls = only_highest_version_dependencies(
            severity_counters.values_list("dependency__purl", flat=True)
        )

        severity_counters = severity_counters.filter(dependency__purl__in=highest_version_vulns_purls)

        for counter in severity_counters:
            if counter["severity"] is not None:
                severities[SCAFinding.Severity(counter["severity"]).label.lower()] = counter["count"]
            else:
                severities["eol"] = counter["count_eol"]

        del severities[SCAFinding.Severity.INFORMATIVE.label.lower()]  # not tracked in counter

        findings_counter, _ = SCAFindingCounter.objects.update_or_create(dependency=self, defaults=severities)
        return findings_counter

    @property
    def dependencies(self) -> list:
        return SCADependency.get_dependencies(self)

    def __str__(self) -> str:
        return self.purl

    class Meta:
        verbose_name = "Dependency (SCA)"
        verbose_name_plural = "Dependencies (SCA)"


class SCAProject(SCADependency):
    class Meta:
        proxy = True
        verbose_name = "Project (SCA)"
        verbose_name_plural = "Projects (SCA)"


class SCAFindingCounter(models.Model):
    dependency = models.OneToOneField(SCADependency, on_delete=models.CASCADE, unique=True)
    critical = models.IntegerField(default=0)
    high = models.IntegerField(default=0)
    medium = models.IntegerField(default=0)
    low = models.IntegerField(default=0)
    eol = models.IntegerField(default=0)
    last_sync = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dependency Finding Counter (SCA)"
        verbose_name_plural = "Dependency Finding Counters (SCA)"


class SCAFinding(vuln_models.Finding):
    class SeverityMapping(Enum):
        NONE = None
        LOW = vuln_models.Finding.Severity.LOW
        MEDIUM = vuln_models.Finding.Severity.MEDIUM
        MODERATE = vuln_models.Finding.Severity.MEDIUM
        HIGH = vuln_models.Finding.Severity.HIGH
        CRITICAL = vuln_models.Finding.Severity.CRITICAL

    class FindingType(models.IntegerChoices):
        VULN = 0
        EOL = 1
        LICENSE = 2

    dependency = models.ForeignKey(SCADependency, on_delete=models.CASCADE)
    vuln_id = models.CharField(max_length=128)
    published = models.DateTimeField()
    aliases = models.TextField(default="")
    fixed_in = models.TextField(default="")
    cvss_vector = models.CharField(max_length=128, default="")
    ecosystem = models.CharField(max_length=20)
    finding_type = models.IntegerField(choices=FindingType.choices, default=FindingType.VULN)

    @property
    def cvss_score(self) -> float:
        return cvss_to_score(self.cvss_vector)

    def __str__(self):
        return self.vuln_id

    class Meta:
        verbose_name = "Dependency Finding (SCA)"
        verbose_name_plural = "Dependency Findings (SCA)"


class SuppressedSCAFinding(models.Model):
    dependency = models.ForeignKey(SCADependency, null=True, on_delete=models.CASCADE)
    vuln_id = models.CharField(max_length=128)
    suppress_reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    updated_by = models.ForeignKey("auth.User", null=True, on_delete=models.SET_NULL, related_name="+")
    sca_project = models.ForeignKey(
        SCAProject, null=True, blank=True, on_delete=models.CASCADE, related_name="suppressed_findings_project"
    )

    class Meta:
        verbose_name = "Suppressed Dependency Finding (SCA)"
        verbose_name_plural = "Suppressed Dependency Findings (SCA)"
        unique_together = ["dependency", "vuln_id"]


@receiver([post_save, post_delete], sender=SuppressedSCAFinding)
def suppressed_sca_finding_post_save_delete(sender, instance, **kwargs):
    if instance.sca_project:
        instance.sca_project.update_vulnerability_counters()
    else:
        for project in instance.dependency.projects:
            project.update_vulnerability_counters()
