from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from logbasecommand.base import LogBaseCommand
from sca.models import SCADependency, SCAFindingCounter


class Command(LogBaseCommand):
    help = "Re-sync SCA Projects Vulnerabilities Counters"

    def handle(self, *args, **options):
        self.sync_time = timezone.now()
        projects = SCADependency.objects.filter(is_project=True).select_related()

        if not projects.exists():
            self.log("No projects found to process.")
            return

        processed_projects = 0
        errors = 0

        # Process in batches to avoid memory issues
        batch_size = 100
        project_list = list(projects)

        for i in range(0, len(project_list), batch_size):
            batch = project_list[i : i + batch_size]
            with transaction.atomic():
                for project in tqdm(batch, desc=f"Updating vulnerability counters (batch {i//batch_size + 1})"):
                    try:
                        project.update_vulnerability_counters()
                        processed_projects += 1
                    except Exception as e:
                        errors += 1
                        self.log_warning(f"Error updating counters for project {project.purl}: {e}")

        # Reset counters for projects that haven't been synced
        stale_counters = SCAFindingCounter.objects.filter(last_sync__lt=self.sync_time)
        stale_count = stale_counters.count()
        if stale_count > 0:
            stale_counters.update(critical=0, high=0, medium=0, low=0, eol=0)

        self.log(
            "Processed vulnerabilities for %s projects. %s errors. %s stale counters reset.",
            processed_projects,
            errors,
            stale_count,
        )
