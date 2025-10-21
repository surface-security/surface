import datetime
from unittest import mock

import responses
from django.conf import settings
from django.core import management
from django.test import TestCase
from django.utils import timezone
from packageurl import PackageURL

from inventory.models import GitSource
from sca.management.commands.resync_sbom_repo import Command
from sca.models import EndOfLifeDependency, SCADependency, SCAFinding, SCAFindingCounter, SuppressedSCAFinding

from . import data


class Test(TestCase):
    @responses.activate
    @mock.patch("django.utils.timezone.now", return_value=datetime.datetime(2023, 9, 7, tzinfo=datetime.timezone.utc))
    def test_resync_sbom_repo(self, now):
        responses.add(
            responses.GET,
            f"{settings.SCA_SBOM_REPO_URL}/urn:uuid:46d764e2-aae1-4f82-b9f1-c616308e921d?vuln_data=True",
            status=200,
            content_type="application/json",
            json=data.sbom_data,
        )

        responses.add(
            responses.GET,
            f"{settings.SCA_SBOM_REPO_URL}/all?since={datetime.datetime.strftime(timezone.now() - timezone.timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%f')}",
            status=200,
            content_type="application/json",
            json=["urn:uuid:46d764e2-aae1-4f82-b9f1-c616308e921d"],
        )

        assert SCAFindingCounter.objects.count() == 0

        management.call_command("resync_sbom_repo")

        # Asserts that the expected 75 dependencies are created
        assert SCADependency.objects.count() == 75
        git_source = GitSource.objects.get(repo_url="https://github.com/test/repo")
        main_dependency = SCADependency.objects.get(purl="pkg:github.com/test/repo@master")

        assert SCAFindingCounter.objects.count() == 1

        # Test SCA Update Vulns Counters
        assert SCAFindingCounter.objects.filter(dependency=main_dependency).exists()
        counter = SCAFindingCounter.objects.filter(dependency=main_dependency).first()
        assert counter.critical == 1
        assert counter.high == 3
        assert counter.medium == 3

        # Asserts  main dependency has only one git source  "https://github.com/test/repo"
        assert main_dependency.git_source == git_source

        # Asserts main dependency has 74 dependencies
        assert main_dependency.depends_on.count() == 30

        # Checks that pkg:pypi/tqdm@4.65.0 does not have depends_on
        assert not SCADependency.objects.get(purl="pkg:pypi/tqdm@4.65.0").depends_on.exists()

        # Test SCAFinding creation
        assert SCAFinding.objects.filter(state=SCAFinding.State.NEW).exists()
        vulnerable_dependency = SCADependency.objects.get(purl="pkg:pypi/django@4.2")

        sca_findings = SCAFinding.objects.filter(dependency=vulnerable_dependency)
        assert sca_findings.count() == 6
        assert sca_findings.filter(state=SCAFinding.State.NEW).count() == 6
        assert sca_findings.filter(severity=SCAFinding.Severity.CRITICAL).count() == 1
        assert sca_findings.filter(severity=SCAFinding.Severity.HIGH).count() == 2
        assert sca_findings.filter(severity=SCAFinding.Severity.MEDIUM).count() == 3

        # Test SCA Finding Suppress
        vuln = SCAFinding.objects.filter(
            dependency=vulnerable_dependency, severity=SCAFinding.Severity.CRITICAL
        ).first()

        SuppressedSCAFinding.objects.create(
            dependency=vulnerable_dependency,
            vuln_id=vuln.vuln_id if vuln else None,
        )
        management.call_command("resync_sbom_repo")

        sca_findings = SCAFinding.objects.filter(dependency=vulnerable_dependency)
        # Asserts SCA Finding was closed as it was Suppressed
        assert sca_findings.filter(state=SCAFinding.State.CLOSED).count() == 1

        # Critical finding was suppressed, so the counter should be updated
        counter = SCAFindingCounter.objects.filter(dependency=main_dependency).first()
        assert counter.critical == 0

    def test_handle_eol_dependency(self):
        eol_date = timezone.now().date() - datetime.timedelta(days=1)
        purl_str = "pkg:pypi/django@3.2.0"
        purl = PackageURL.from_string(purl_str)

        eol_dependency = EndOfLifeDependency.objects.create(
            product="django",
            cycle="3.2.0",
            release_date=timezone.now().date() - datetime.timedelta(days=10),
            eol=eol_date,
            latest_version="3.2.8",
        )

        last_scan_date = timezone.now()

        dependency = SCADependency.objects.create(
            purl=purl, name="django", version="3.2.0", dependency_type="library", last_scan=last_scan_date
        )

        # Test directly handle_eol
        cmd = Command()
        cmd.sync_time = timezone.now()
        cmd.handle_eol(purl, dependency)

        findings = SCAFinding.objects.filter(dependency=dependency, finding_type=SCAFinding.FindingType.EOL)
        assert findings.exists(), "EoL finding was not created for an EoL dependency"

        finding = findings.first()
        assert finding.title == f"{purl.name} {purl.version} is EoL", "Incorrect EoL finding title"
        assert eol_dependency.cycle in finding.summary, "The EoL finding summary does not correctly mention the cycle"
