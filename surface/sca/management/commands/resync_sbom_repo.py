from datetime import datetime
from typing import Any

import requests
import semver
from django.conf import settings
from django.core.management.base import CommandParser
from django.utils import timezone
from packageurl import PackageURL
from tqdm import tqdm

from logbasecommand.base import LogBaseCommand
from sca.models import EndOfLifeDependency, SCADependency, SCAFinding, SuppressedSCAFinding
from sca.utils import cvss_to_severity
from inventory.models import GitSource

MINIMUM_SEVERITY = SCAFinding.Severity.MEDIUM


class Command(LogBaseCommand):
    help = "Re-sync Sbom Repo Components"

    exited_earlier_no_component = 0
    exited_earlier_not_master = 0
    processed = 0
    has_exception = 0

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--since", type=int, default=1, help="Sboms generated since given X hours ago (default=1)")
        parser.add_argument("--uuid", type=str, default=None, help="Sync only given sbom uuid")

    def get_sboms(self, since: datetime) -> list[str]:
        since_str = datetime.strftime(since, "%Y-%m-%dT%H:%M:%S.%f")
        res = requests.get(f"http://{settings.SCA_SBOM_REPO_URL}/all", params={"since": since_str})
        res.raise_for_status()
        return res.json()

    def get_sbom_details(self, serial_number: str) -> dict[str, Any]:
        res = requests.get(f"http://{settings.SCA_SBOM_REPO_URL}/{serial_number}", params={"vuln_data": True})
        res.raise_for_status()
        return res.json()

    def create_dependency(self, purl: str, scan_date: str) -> tuple[PackageURL | None, SCADependency | None]:
        if not purl:
            return None, None
        try:
            purl = PackageURL.from_string(purl)
        except ValueError:
            self.log_exception("could not parse purl %s in dependencies", purl)
            return None, None
        dep_object, _ = SCADependency.objects.update_or_create(
            purl=purl,
            defaults={
                "dependency_type": "dependency",
                "name": purl.name,
                "version": purl.version or "",
                "last_scan": scan_date,
            },
        )

        return purl, dep_object

    # Check for EOL dependencies
    def handle_eol(self, purl: PackageURL, dependency: SCADependency):
        # Get Suppressed Findings for current dependency
        suppressed_findings = SuppressedSCAFinding.objects.filter(dependency=dependency)
        eol_dependencies = EndOfLifeDependency.objects.filter(product=purl.name, eol__lt=datetime.now().date())

        for eol in eol_dependencies:
            try:
                eol_version = semver.Version.parse(eol.cycle, optional_minor_and_patch=True)
                purl_version = semver.Version.parse(
                    ".".join(purl.version.split(".")[:3]), optional_minor_and_patch=True
                )
            except ValueError:
                self.log_warning("Error processing EOL", exc_info=True)
                continue

            if purl_version.is_compatible(eol_version):
                SCAFinding.objects.update_or_create(
                    dependency=dependency,
                    vuln_id=eol.pk,
                    defaults={
                        "title": f"{purl.name} {purl.version} is EoL",
                        "summary": f"{purl.name} is End of Life for version {purl.version}",
                        "finding_type": SCAFinding.FindingType.EOL,
                        "published": eol.eol,
                        "ecosystem": purl.type,
                        "state": (
                            SCAFinding.State.NEW
                            if not suppressed_findings.filter(vuln_id=eol.pk)
                            else SCAFinding.State.CLOSED
                        ),
                        "last_seen_date": self.sync_time,
                    },
                )
                break

    def handle_vuln(self, vuln: dict[str, Any], pkg_obj: SCADependency):
        # Get Suppressed Findings for current dependency
        suppressed_findings = SuppressedSCAFinding.objects.filter(dependency=pkg_obj)
        cvss3 = [sev["score"] for sev in vuln.get("severity", []) if sev["type"] == "CVSS_V3"]
        severity = vuln.get("database_specific", {}).get("severity") or vuln.get("system_specific", {}).get("severity")

        if not severity and cvss3:
            severity = cvss_to_severity(cvss3[0])
        elif not severity:
            severity = "NONE"

        severity_mapped = SCAFinding.SeverityMapping[severity.upper()].value
        if not severity_mapped or severity_mapped < MINIMUM_SEVERITY:
            return False

        fixed_in = [
            event["fixed"]
            for version in vuln.get("affected", {})
            for version_range in version.get("ranges", {})
            for event in version_range.get("events", {})
            if "fixed" in event
        ]

        SCAFinding.objects.update_or_create(
            dependency=pkg_obj,
            vuln_id=vuln["id"],
            defaults={
                # the dependency tree instead
                "published": vuln["published"],
                "cvss_vector": cvss3[0] if cvss3 else "",
                "finding_type": SCAFinding.FindingType.VULN,
                "title": vuln.get("summary", "").capitalize(),
                "summary": vuln["details"],
                "state": (
                    SCAFinding.State.NEW
                    if not suppressed_findings.filter(vuln_id=vuln["id"])
                    else SCAFinding.State.CLOSED
                ),
                "aliases": ", ".join(vuln.get("aliases", [])),
                "fixed_in": ", ".join(fixed_in) if fixed_in else "",
                "last_seen_date": self.sync_time,
                "severity": severity_mapped,
            },
        )

    def handle_sbom(self, sbom: str) -> bool:
        sbom_data = self.get_sbom_details(sbom)

        repo = sbom_data["sbomrepo"]["metadata"]["repo"]
        branch = sbom_data["sbomrepo"]["metadata"].get("branch", "master")
        main_branch = sbom_data["sbomrepo"]["metadata"].get("main_branch", "master")

        project = None
        main_dependencies = set()
        secondary_dependencies = set()

        if branch != main_branch:
            self.log_warning(f'{sbom} skiped for repo: {sbom_data["sbomrepo"]["metadata"]["repo"]}, branch: {branch}')
            self.exited_earlier_not_master += 1
            return False

        if "component" not in sbom_data["metadata"]:
            self.log_error(f"Component Not found for {sbom_data['serialNumber']}")
            self.exited_earlier_no_component += 1
            return False

        # cleanup old dependencies because current ones will be added, no history needed
        existing_dependencies = SCADependency.objects.filter(git_source__repo_url=repo)
        git_source = GitSource.objects.filter(repo_url=repo, branch=branch, active=True).first()
        if git_source:
            for existing_dep in existing_dependencies:
                existing_dep.git_source = None
                existing_dep.save()
        else:
            git_source, _ = GitSource.objects.update_or_create(
                repo_url=repo,
                branch=branch,
                defaults={
                    "active": True,
                },
            )

        for component in sbom_data.get("components", []):
            purl, _ = self.create_dependency(component["purl"], sbom_data["metadata"]["timestamp"])
            main_dependencies.add(component["purl"])

        for dependency in sbom_data.get("dependencies", []):
            depends_on = set()
            purl, dep_object = self.create_dependency(dependency["ref"], sbom_data["metadata"]["timestamp"])
            if not purl:
                continue

            if purl.type in settings.SCA_SOURCE_PURL_TYPES and f"{purl.namespace}/{purl.name}" in repo:
                dep_object.git_source = git_source
                dep_object.is_project = True
                dep_object.save()

                project = dep_object
            else:
                main_dependencies.add(dep_object.purl)

            self.handle_eol(purl, dep_object)

            dep_object.depends_on.clear()

            for dep in dependency.get("dependsOn", []):
                purl, sec_dep = self.create_dependency(dep, sbom_data["metadata"]["timestamp"])
                if not purl:
                    continue
                depends_on.add(sec_dep)
                secondary_dependencies.add(sec_dep.purl)

                self.handle_eol(purl, sec_dep)

            dep_object.depends_on.add(*depends_on)

        if project:
            project.depends_on.add(*SCADependency.objects.filter(purl__in=main_dependencies - secondary_dependencies))

        for pkg, vulns in sbom_data["sbomrepo"].get("vulnerabilities", {}).items():
            try:
                purl = PackageURL.from_string(pkg)
            except ValueError:
                self.log_exception("could not parse purl %s in vulnerabilities", pkg)
                continue

            purl, pkg_obj = self.create_dependency(pkg, sbom_data["metadata"]["timestamp"])

            for vuln in vulns:
                self.handle_vuln(vuln, pkg_obj)

        if project:
            project.update_vulnerability_counters()

        self.processed += 1
        return True
        # delete dependencies that are not a dependency of others and don't have gitsource¯

    def handle(self, *args, **options):
        self.sync_time = timezone.now()

        if options["uuid"]:
            sboms = [options["uuid"]]
        else:
            since = self.sync_time - timezone.timedelta(hours=options["since"])
            sboms = self.get_sboms(since)

        for sbom in tqdm(sboms):
            try:
                self.handle_sbom(sbom)
            except Exception:
                self.has_exception += 1
                self.log_exception("Could not sync data for sbom: %s", sbom)

        self.log(
            "%s SBOMs successfully processed, "
            "%s exited earlier without component, "
            "%s exited earlier due to branch condition, "
            "%s raised an exception",
            self.processed,
            self.exited_earlier_no_component,
            self.exited_earlier_not_master,
            self.has_exception,
        )
