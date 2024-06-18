from datetime import datetime

import responses
from django.core import management
from django.test import TestCase

from sca import models


class Test(TestCase):
    @responses.activate
    def test_resync_endoflife(self):
        responses.add(
            responses.GET,
            "https://endoflife.date/api/all.json",
            status=200,
            content_type="application/json",
            json=["django", "tomcat"],
        )
        responses.add(
            responses.GET,
            "https://endoflife.date/api/django.json",
            status=200,
            content_type="application/json",
            json=[
                {
                    "cycle": "4.2",
                    "support": "2023-12-01",
                    "eol": "2056-04-01",
                    "latest": "4.2.2",
                    "lts": True,
                    "latestReleaseDate": "2023-06-05",
                    "releaseDate": "2023-04-03",
                },
                {
                    "cycle": "4.1",
                    "support": "2023-04-01",
                    "eol": "2022-12-01",
                    "latest": "4.1.9",
                    "latestReleaseDate": "2022-12-03",
                    "releaseDate": "2022-08-03",
                    "lts": False,
                },
            ],
        )

        responses.add(
            responses.GET,
            "https://endoflife.date/api/tomcat.json",
            status=200,
            content_type="application/json",
            json=[
                {
                    "cycle": "10.1",
                    "releaseDate": "2022-09-23",
                    "eol": True,
                    "minJavaVersion": 11,
                    "latest": "10.1.10",
                    "latestReleaseDate": "2023-06-02",
                    "lts": False,
                },
                {
                    "cycle": "10.0",
                    "releaseDate": "2020-12-03",
                    "eol": False,
                    "minJavaVersion": 8,
                    "latest": "10.0.27",
                    "latestReleaseDate": "2022-10-03",
                    "lts": False,
                },
            ],
        )

        assert models.EndOfLifeDependency.objects.count() == 0

        management.call_command("resync_endoflife")

        # Given the data two django entries should be created and one of them should be EOL ("eol": "2056-04-01")
        assert models.EndOfLifeDependency.objects.filter(product="django").count() == 2
        assert models.EndOfLifeDependency.objects.filter(product="django", eol__lte=datetime.now().date()).count() == 1
        # Asserts No Django product has datetime.min or datetime.max on eol as both examples have given dates
        assert (
            models.EndOfLifeDependency.objects.filter(product="django", eol__in=(datetime.min, datetime.max)).count()
            == 0
        )

        # 2 Tomcat products should be created
        assert models.EndOfLifeDependency.objects.filter(product="tomcat").count() == 2
        # Asserts tomcat products have datetime.min on eol as both examples have no given dates and EOL is True
        assert models.EndOfLifeDependency.objects.filter(product="tomcat", eol=datetime.min).count() == 1
        # Asserts tomcat product has datetime.max on eol comes as False
        assert models.EndOfLifeDependency.objects.filter(product="tomcat", eol=datetime.max).count() == 1
