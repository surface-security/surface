import cvss
import pytest
from django.test import TestCase

from sca.utils import cvss_to_score, cvss_to_severity, only_highest_version_dependencies


class Test(TestCase):
    def test_cvss_to_severity(self):
        assert cvss_to_severity("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H") == "Critical"  # CVE-2021-44228 Log4j
        assert cvss_to_severity("AV:N/AC:M/Au:N/C:C/I:C/A:C") == "High"  # CVE-2021-44228 Log4j
        assert cvss_to_severity("CVSS:3.0/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N") == "Medium"  # CVE-2013-1937 Wordpress

        with pytest.raises(cvss.exceptions.CVSSError):
            cvss_to_severity("bogus")

    def test_cvss_to_score(self):
        assert cvss_to_score("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H") == 10.0  # CVE-2021-44228 Log4j
        assert cvss_to_score("AV:N/AC:M/Au:N/C:C/I:C/A:C") == 9.3  # CVE-2021-44228 Log4j

    def test_only_highest_version_dependencies(self):
        assert only_highest_version_dependencies(
            [
                "pkg:pypi/django@3.0.2",
                "pkg:pypi/django@4.2.3",
            ]
        ) == ["pkg:pypi/django@4.2.3"]
