import requests
import tqdm
from packageurl import PackageURL

from logbasecommand.base import LogBaseCommand
from sca.models import SCADependency


class Command(LogBaseCommand):
    help = "Check Public Dependencies"

    def check_public_dependency(self, package_name: str, repository: str) -> bool:
        if repository == "npm":
            response = requests.get(f"https://registry.npmjs.org/{package_name}")
            return response.status_code == 200
        elif repository == "maven":
            response = requests.get(f'https://search.maven.org/solrsearch/select?q=g:"{package_name}"')
            return response.status_code == 200 and response.json()["response"]["numFound"] > 0
        elif repository == "pypi":
            response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
            return response.status_code == 200
        elif repository == "rubygems":
            response = requests.get(f"https://rubygems.org/api/v1/gems/{package_name}.json")
            return response.status_code == 200
        elif repository == "nuget":
            response = requests.get(
                f"https://azuresearch-usnc.nuget.org/query?q=packageid:{package_name}&prerelease=false"
            )
            return response.status_code == 200 and response.json()["totalHits"] > 0
        else:
            raise ValueError("Invalid repository type")

    def handle(self, *args, **options):
        for dependency in tqdm.tqdm(SCADependency.objects.filter(is_public=False).exclude(is_project=True)):
            try:
                purl = PackageURL.from_string(dependency.purl)
                dependency.is_public = self.check_public_dependency(purl.name, purl.type)
                dependency.save()
            except ValueError:
                continue
