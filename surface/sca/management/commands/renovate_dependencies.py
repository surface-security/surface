import json
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import CommandError

from logbasecommand.base import LogBaseCommand


class Command(LogBaseCommand):
    help = "Runs the Renovate bot on specified repositories using the Renovate Docker image."

    def add_arguments(self, parser):
        parser.add_argument("git_urls", type=str, nargs="+", help="The repository URLs to process.")
        parser.add_argument("--dependencies", nargs="+", help="Optional list of dependencies", default=[])
        parser.add_argument("--local", action="store_true", help="Run the command locally")

    def handle(self, *args, **options):
        git_urls = options["git_urls"]
        dependencies = options["dependencies"]
        is_local = options["local"]

        platforms = {self.parse_git_url(url)[0] for url in git_urls}
        if len(platforms) > 1:
            self.log_error("All repositories must be from the same platform.")
            return

        platform = platforms.pop()
        repo_urls = [self.parse_git_url(url)[1] for url in git_urls]

        temp_config_path = self.create_temp_renovate_config(repo_urls, dependencies, is_local)
        try:
            result = self.run_docker(platform, temp_config_path, is_local)
            if not result:
                raise CommandError("Failed to execute Renovate")
            self.log(f"Successfully executed Renovate for: {repo_urls}")
        finally:
            Path(temp_config_path).unlink()

    def parse_git_url(self, git_url: str):
        repo_url = git_url.split("//")[1]
        platform_domain = repo_url.split("/")[0]
        platform = "gitlab" if "gitlab" in platform_domain else "github"
        repo_path = "/".join(repo_url.split("/")[1:])
        return platform, repo_path

    def create_temp_renovate_config(self, repo_urls: list, dependencies=None, is_local=False):
        if dependencies is None:
            dependencies = []
        current_script_dir = Path(__file__).parent

        template_filename = "renovate_vulnerable.json" if dependencies else "renovate.json"
        template_path = current_script_dir / ".." / "renovate" / template_filename

        with template_path.open("r") as file:
            config = json.load(file)

        config["repositories"] = repo_urls

        unique_dependencies = set()
        if isinstance(dependencies, list):
            for dep in dependencies:
                name = dep.split("/")[-1].split("@")[0]
                unique_dependencies.add(name)
        elif isinstance(dependencies, str):
            name = dependencies.split("/")[-1].split("@")[0]
            unique_dependencies.add(name)
        else:
            raise ValueError("Dependencies must be a list or a string")

        sorted_dependencies = sorted(unique_dependencies)
        dep_pattern = f"^(?i)({'|'.join(sorted_dependencies)})$"
        config["packageRules"][1]["matchPackagePatterns"] = [dep_pattern]

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        temp_file_path = Path("/renovate") / f"renovate_config_{timestamp}.json"

        if is_local:
            temp_file_path = Path.cwd() / f"renovate_config_{timestamp}.json"

        temp_file_path.parent.mkdir(exist_ok=True)
        with temp_file_path.open("w") as temp_file:
            json.dump(config, temp_file, indent=4)

        return str(temp_file_path)

    def run_docker(self, platform: str, temp_config_path: str, is_local: bool) -> bool:
        token = settings.SURFACE_GITHUB_TOKEN if platform == "github" else settings.SURFACE_GITLAB_TOKEN
        endpoint = "https://api.github.com" if platform == "github" else settings.SCA_INTERNAL_GITLAB_API

        if not token:
            self.log_error(f"Token for {platform} is not configured in settings")
            return False

        docker_image = settings.SCA_INTERNAL_RENOVATE if settings.SCA_INTERNAL_RENOVATE else "renovate/renovate"

        if is_local:
            docker_temp_config_path = Path("/usr/src/app") / Path(temp_config_path).name
            command = f"docker run --rm -v {Path.cwd()}:/usr/src/app -e LOG_LEVEL=debug -e RENOVATE_TOKEN={token} -e RENOVATE_CONFIG_FILE={docker_temp_config_path} -e RENOVATE_PLATFORM={platform} -e RENOVATE_ENDPOINT={endpoint} {docker_image}"
        else:
            command = f"/usr/bin/docker run --rm -v /renovate:/renovate -e RENOVATE_TOKEN={token} -e RENOVATE_CONFIG_FILE={temp_config_path} -e RENOVATE_PLATFORM={platform} -e RENOVATE_ENDPOINT={endpoint} {docker_image}"

        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            if result.stdout:
                self.log("Docker output: %s", result.stdout)
        except subprocess.CalledProcessError as ex:
            self.log_exception("Failed to execute Docker command: %s", ex.stderr)
            return False
        return True
