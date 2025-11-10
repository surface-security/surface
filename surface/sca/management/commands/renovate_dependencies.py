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

        temp_config_path = self.create_temp_renovate_config(repo_urls, dependencies, is_local, platform)
        try:
            result = self.run_docker(platform, temp_config_path, is_local)
            if not result:
                raise CommandError("Failed to execute Renovate")
            self.log(f"Successfully executed Renovate for: {repo_urls}")
        finally:
            Path(temp_config_path).unlink()

    def parse_git_url(self, git_url: str):
        """Parse git URL to extract platform and repository path.

        Args:
            git_url: Git URL in format like https://github.com/owner/repo or https://gitlab.com/owner/repo

        Returns:
            tuple: (platform, repo_path) where platform is 'github' or 'gitlab'

        Raises:
            ValueError: If URL format is invalid
        """
        if "//" not in git_url:
            raise ValueError(f"Invalid git URL format: {git_url}")
        repo_url = git_url.split("//", 1)[1]
        if "/" not in repo_url:
            raise ValueError(f"Invalid git URL format: {git_url}")
        platform_domain = repo_url.split("/")[0]
        platform = "gitlab" if "gitlab" in platform_domain else "github"
        repo_path = "/".join(repo_url.split("/")[1:])
        if not repo_path:
            raise ValueError(f"Invalid git URL format: {git_url}")
        return platform, repo_path

    def create_temp_renovate_config(self, repo_urls: list, dependencies=None, is_local=False, platform=None):
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

        if unique_dependencies:
            sorted_dependencies = sorted(unique_dependencies)
            dep_pattern = f"^(?i)({'|'.join(sorted_dependencies)})$"
            config["packageRules"][1]["matchPackagePatterns"] = [dep_pattern]
            if platform == "github":
                config["prTitle"] = "Update vulnerable dependencies"

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

        _env = {
            "RENOVATE_TOKEN": token,
            "RENOVATE_PLATFORM": platform,
            "RENOVATE_ENDPOINT": endpoint,
        }
        if is_local:
            docker_temp_config_path = Path("/usr/src/app") / Path(temp_config_path).name
            _env["RENOVATE_CONFIG_FILE"] = docker_temp_config_path
            _env["LOG_LEVEL"] = "debug"
            command = (
                f"docker run --rm -v {Path.cwd()}:/usr/src/app "
                f"-e RENOVATE_TOKEN -e RENOVATE_PLATFORM -e RENOVATE_ENDPOINT "
                f"-e RENOVATE_CONFIG_FILE -e LOG_LEVEL {docker_image}"
            )
        else:
            _env["RENOVATE_CONFIG_FILE"] = temp_config_path
            command = (
                f"/usr/bin/docker run --rm -v /renovate:/renovate "
                f"-e RENOVATE_TOKEN -e RENOVATE_PLATFORM "
                f"-e RENOVATE_ENDPOINT -e RENOVATE_CONFIG_FILE {docker_image}"
            )

        try:
            result = subprocess.run(
                command,
                shell=True,  # Required for docker volume mounts
                check=True,
                capture_output=True,
                text=True,
                env=_env,
                timeout=3600,  # 1 hour timeout
            )
            if result.stdout:
                self.log("Docker output: %s", result.stdout)
            if result.stderr:
                self.log_error("Docker error: %s", result.stderr)
        except subprocess.TimeoutExpired:
            self.log_error("Docker command timed out after 1 hour")
            return False
        except subprocess.CalledProcessError as ex:
            self.log_exception("Failed to execute Docker command: %s", ex.output if hasattr(ex, 'output') else str(ex))
            return False
        return True
