import tqdm
from django.utils import timezone

from logbasecommand.base import LogBaseCommand
from sca.models import SCADependency, SCAFindingCounter


class Command(LogBaseCommand):
    help = "Re-sync SCA Projects Vulnerabilities Counters"

    processed_projects = 0

    def handle(self, *args, **options):
        self.sync_time = timezone.now()
        for project in tqdm.tqdm(SCADependency.objects.filter(is_project=True)):
            project.update_vulnerability_counters()
            self.processed_projects += 1

        SCAFindingCounter.objects.filter(last_sync__lt=self.sync_time).update(
            critical=0, high=0, medium=0, low=0, eol=0
        )

        self.log(
            "Processed Vulnerabilities for %s projects.",
            self.processed_projects,
        )
