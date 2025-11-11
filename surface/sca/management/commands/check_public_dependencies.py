from typing import Callable, Dict

import requests
from packageurl import PackageURL
from tqdm import tqdm

from logbasecommand.base import LogBaseCommand
from sca.models import SCADependency
from sca.utils import create_http_session


class Command(LogBaseCommand):
    help = "Check Public Dependencies"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = create_http_session()
        self._checkers: Dict[str, Callable[[str], bool]] = {
            "npm": self._check_npm,
            "maven": self._check_maven,
            "pypi": self._check_pypi,
            "rubygems": self._check_rubygems,
            "nuget": self._check_nuget,
            "composer": self._check_composer,
            "cargo": self._check_cargo,
            "golang": self._check_golang,
            "hex": self._check_hex,
            "conan": self._check_conan,
            "cocoapods": self._check_cocoapods,
            "pub": self._check_pub,
        }

    def _check_npm(self, package_name: str) -> bool:
        response = self.session.get(f"https://registry.npmjs.org/{package_name}", timeout=10)
        return response.status_code == 200

    def _check_maven(self, package_name: str) -> bool:
        response = self.session.get(f'https://search.maven.org/solrsearch/select?q=g:"{package_name}"', timeout=10)
        return response.status_code == 200 and response.json().get("response", {}).get("numFound", 0) > 0

    def _check_pypi(self, package_name: str) -> bool:
        response = self.session.get(f"https://pypi.org/pypi/{package_name}/json", timeout=10)
        return response.status_code == 200

    def _check_rubygems(self, package_name: str) -> bool:
        response = self.session.get(f"https://rubygems.org/api/v1/gems/{package_name}.json", timeout=10)
        return response.status_code == 200

    def _check_nuget(self, package_name: str) -> bool:
        response = self.session.get(
            f"https://azuresearch-usnc.nuget.org/query?q=packageid:{package_name}&prerelease=false", timeout=10
        )
        return response.status_code == 200 and response.json().get("totalHits", 0) > 0

    def _check_composer(self, package_name: str) -> bool:
        response = self.session.get(f"https://packagist.org/packages/{package_name}.json", timeout=10)
        return response.status_code == 200

    def _check_cargo(self, package_name: str) -> bool:
        response = self.session.get(f"https://crates.io/api/v1/crates/{package_name}", timeout=10)
        return response.status_code == 200

    def _check_golang(self, package_name: str) -> bool:
        response = self.session.get(f"https://proxy.golang.org/{package_name}/@v/list", timeout=10)
        return response.status_code == 200 and len(response.text.strip()) > 0

    def _check_hex(self, package_name: str) -> bool:
        response = self.session.get(f"https://hex.pm/api/packages/{package_name}", timeout=10)
        return response.status_code == 200

    def _check_conan(self, package_name: str) -> bool:
        response = self.session.get(f"https://conan.io/center/v1/packages/search?q={package_name}", timeout=10)
        return response.status_code == 200 and len(response.json().get("items", [])) > 0

    def _check_cocoapods(self, package_name: str) -> bool:
        response = self.session.get(f"https://trunk.cocoapods.org/api/v1/pods/{package_name}", timeout=10)
        return response.status_code == 200

    def _check_pub(self, package_name: str) -> bool:
        response = self.session.get(f"https://pub.dev/api/packages/{package_name}", timeout=10)
        return response.status_code == 200

    def check_public_dependency(self, package_name: str, repository: str) -> bool:
        """Check if a package is publicly available in the given repository."""
        checker = self._checkers.get(repository)
        if not checker:
            self.log_warning(f"Unsupported repository type: {repository}")
            return False

        try:
            return checker(package_name)
        except (requests.RequestException, KeyError, ValueError) as e:
            self.log_warning(f"Error checking {repository} package {package_name}: {e}")
            return False

    def handle(self, *args, **options):
        dependencies = SCADependency.objects.filter(is_public=False).exclude(is_project=True)
        updated = 0
        errors = 0

        for dependency in tqdm(dependencies, desc="Checking public dependencies"):
            try:
                purl = PackageURL.from_string(dependency.purl)
                dependency.is_public = self.check_public_dependency(purl.name, purl.type)
                dependency.save(update_fields=["is_public"])
                updated += 1
            except ValueError as e:
                self.log_warning(f"Could not parse purl {dependency.purl}: {e}")
                errors += 1
                continue

        self.log(f"Updated {updated} dependencies. {errors} errors.")
