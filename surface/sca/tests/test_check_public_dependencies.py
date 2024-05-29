import responses
from django.core import management
from django.test import TestCase
from django.utils import timezone

from sca.models import SCADependency


class Test(TestCase):
    @responses.activate
    def test_check_public_dependencies(self):
        # pypi.org
        responses.add(
            responses.GET,
            "https://pypi.org/pypi/pypidep/json",
            status=200,
        )
        responses.add(
            responses.GET,
            "https://pypi.org/pypi/pypidep-internal/json",
            status=404,
        )

        # registry.npmjs.org
        responses.add(
            responses.GET,
            "https://registry.npmjs.org/npmdep",
            status=200,
        )
        responses.add(
            responses.GET,
            "https://registry.npmjs.org/npmdep-internal",
            status=404,
        )

        # search.maven.org
        responses.add(
            responses.GET,
            'https://search.maven.org/solrsearch/select?q=g:"mavendep"',
            status=200,
            json={"response": {"numFound": 1}},
        )
        responses.add(
            responses.GET,
            'https://search.maven.org/solrsearch/select?q=g:"mavendep-internal"',
            status=200,
            json={"response": {"numFound": 0}},
        )

        # rubygems.org
        responses.add(
            responses.GET,
            "https://rubygems.org/api/v1/gems/rubydep.json",
            status=200,
        )
        responses.add(
            responses.GET,
            "https://rubygems.org/api/v1/gems/rubydep-internal.json",
            status=404,
        )

        # azuresearch-usnc.nuget.org
        responses.add(
            responses.GET,
            "https://azuresearch-usnc.nuget.org/query?q=packageid:nugetdep&prerelease=false",
            json={"totalHits": 1},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://azuresearch-usnc.nuget.org/query?q=packageid:nugetdep-internal&prerelease=false",
            json={"totalHits": 0},
            status=200,
        )

        # create pypi dependencies
        SCADependency.objects.create(purl="pkg:pypi/pypidep@1.0", last_scan=timezone.datetime.now())
        SCADependency.objects.create(purl="pkg:pypi/pypidep-internal@1.0", last_scan=timezone.datetime.now())

        # create npm dependencies
        SCADependency.objects.create(purl="pkg:npm/npmdep@1.0", last_scan=timezone.datetime.now())
        SCADependency.objects.create(purl="pkg:npm/npmdep-internal@1.0", last_scan=timezone.datetime.now())

        # create maven dependencies
        SCADependency.objects.create(purl="pkg:maven/mavendep@1.0", last_scan=timezone.datetime.now())
        SCADependency.objects.create(purl="pkg:maven/mavendep-internal@1.0", last_scan=timezone.datetime.now())

        # create rubygems dependencies
        SCADependency.objects.create(purl="pkg:rubygems/rubydep@1.0", last_scan=timezone.datetime.now())
        SCADependency.objects.create(purl="pkg:rubygems/rubydep-internal@1.0", last_scan=timezone.datetime.now())

        # create nuget dependencies
        SCADependency.objects.create(purl="pkg:nuget/nugetdep@1.0", last_scan=timezone.datetime.now())
        SCADependency.objects.create(purl="pkg:nuget/nugetdep-internal@1.0", last_scan=timezone.datetime.now())

        management.call_command("check_public_dependencies")

        # asserts 1 public and 1 internal for each repository
        assert SCADependency.objects.get(purl="pkg:pypi/pypidep@1.0").is_public is True
        assert SCADependency.objects.get(purl="pkg:pypi/pypidep-internal@1.0").is_public is False

        assert SCADependency.objects.get(purl="pkg:npm/npmdep@1.0").is_public is True
        assert SCADependency.objects.get(purl="pkg:npm/npmdep-internal@1.0").is_public is False

        assert SCADependency.objects.get(purl="pkg:maven/mavendep@1.0").is_public is True
        assert SCADependency.objects.get(purl="pkg:maven/mavendep-internal@1.0").is_public is False

        assert SCADependency.objects.get(purl="pkg:rubygems/rubydep@1.0").is_public is True
        assert SCADependency.objects.get(purl="pkg:rubygems/rubydep-internal@1.0").is_public is False

        assert SCADependency.objects.get(purl="pkg:nuget/nugetdep@1.0").is_public is True
        assert SCADependency.objects.get(purl="pkg:nuget/nugetdep-internal@1.0").is_public is False
