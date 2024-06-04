from datetime import datetime
from unittest import mock

import responses
from django.apps import apps
from django.conf import settings
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.core import management
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from sca.apps import SCAConfig
from sca.models import SCADependency
from sca.tests import data


class Test(TestCase):
    @responses.activate
    @mock.patch("django.utils.timezone.now", return_value=datetime(2023, 9, 7, tzinfo=timezone.utc))
    def setUp(self, now) -> None:
        self.user = get_user_model().objects.create_user("tester", "tester@ppb.it", "tester")
        self.site = AdminSite()
        responses.add(
            responses.GET,
            f"http://{settings.SCA_SBOM_REPO_URL}/urn:uuid:46d764e2-aae1-4f82-b9f1-c616308e921d?vuln_data=True",
            status=200,
            content_type="application/json",
            json=data.sbom_data,
        )

        responses.add(
            responses.GET,
            f"http://{settings.SCA_SBOM_REPO_URL}/all?since={datetime.strftime(timezone.now() - timezone.timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%f')}",
            status=200,
            content_type="application/json",
            json=["urn:uuid:46d764e2-aae1-4f82-b9f1-c616308e921d"],
        )

        management.call_command("resync_sbom_repo")

        self.sca_project = SCADependency.objects.filter(is_project=True).first()
        self.admin_change_url = reverse("admin:sca_scaproject_change", args=[self.sca_project.pk])

    def make_user_admin(self):
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()

    def test_apps(self):
        assert SCAConfig.name == "sca"
        assert apps.get_app_config("sca").name == "sca"
        apps.get_app_config("sca").ready()

    def test_admin_changelist(self):
        r = self.client.get(reverse("admin:sca_scaproject_changelist"))
        assert r.status_code == 302

        self.make_user_admin()
        self.client.login(username="tester", password="tester")

        r = self.client.get(reverse("admin:sca_scaproject_changelist"))

        assert SCADependency.objects.filter(is_project=True).count() == 1

        # Assert specific HTML content
        content = r.content.decode()
        assert "pkg:github.com/test/repo@master" in content
        assert "https://github.com/test/repo" in content
        assert "<span>Vulnerabilities</span>" in content
        assert "1 Project (SCA)" in content

        # Assert Vulnerabilities Counters
        assert "1 Critical" in content
        assert "4 High" in content
        assert "3 Medium" in content
        assert "0 Low" in content
        assert "0 End of Life" in content

    def test_admin_changeview_dependencies(self):
        r = self.client.get(reverse("admin:sca_scaproject_changelist"))
        assert r.status_code == 302

        self.make_user_admin()
        self.client.login(username="tester", password="tester")

        response = self.client.get(self.admin_change_url)
        assert response.status_code == 200

        content = response.content.decode()

        # Assert SCA Project name in HTML content
        assert "pkg:github.com/test/repo@master" in content

        # Assert right links in secundary menu
        assert f'href="/sca/scaproject/{self.sca_project.pk}/change/' in content
        assert f'href="/sca/scaproject/{self.sca_project.pk}/change/?view=vulnerabilities' in content

        # Assert dependencies in table
        assert "pkg:pypi/django@4.2" in content
        assert "pkg:pypi/setuptools@53.0.0" in content
        assert "pkg:pypi/pytest@7.4.0" in content

        # Assert Vulnerabilities Counters for pkg:pypi/django@4.2
        assert "1 Critical" in content
        assert "2 High" in content
        assert "3 Medium" in content

        # Test Vulnerabile Filter
        response = self.client.get(self.admin_change_url + "?show_vulnerable=True")
        assert response.status_code == 200

        content = response.content.decode()

        # Assert only vulnerable dependencies in table
        assert "pkg:pypi/django@4.2" in content
        assert "pkg:pypi/setuptools@53.0.0" in content
        assert "pkg:pypi/pytest@7.4.0" not in content

        # only vulnerable dependencies in table and django
        response = self.client.get(self.admin_change_url + "?purl=Django&show_vulnerable=True")
        assert response.status_code == 200

        content = response.content.decode()

        # Assert only dango in table
        assert "pkg:pypi/django@4.2" in content
        assert "pkg:pypi/setuptools@53.0.0" not in content
        assert "pkg:pypi/pytest@7.4.0" not in content

        # Is Public Filter
        SCADependency.objects.all().update(is_public=True)

        response = self.client.get(self.admin_change_url + "?is_public=false")
        assert response.status_code == 200

        content = response.content.decode()

        # Assert no dependencies in table
        assert "No Dependencies found" in content

    def test_admin_changeview_vulnerabilities(self):
        r = self.client.get(reverse("admin:sca_scaproject_changelist"))
        assert r.status_code == 302

        self.make_user_admin()
        self.client.login(username="tester", password="tester")
        response = self.client.get(self.admin_change_url + "?view=vulnerabilities")

        assert response.status_code == 200

        content = response.content.decode()

        assert "pkg:pypi/django@4.2" in content
        assert "pkg:pypi/setuptools@53.0.0" in content

        # Severity Filter
        response = self.client.get(self.admin_change_url + "?view=vulnerabilities&is_public=false&severity=5")
        content = response.content.decode()

        assert "pkg:pypi/django@4.2" in content
        assert "pkg:pypi/setuptools@53.0.0" not in content

        # Fixable Filter
        response = self.client.get(
            self.admin_change_url + "?view=vulnerabilities&is_public=false&severity=5&fixed_in=false"
        )
        content = response.content.decode()

        assert "No vulnerabilities found" in content
