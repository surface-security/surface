import requests
from django.utils import timezone
from tqdm import tqdm

from logbasecommand.base import LogBaseCommand
from sca import models


class Command(LogBaseCommand):
    help = "Re-sync End Of Life packages from https://endoflife.date"

    def add_arguments(self, parser):
        parser.add_argument("--no-progress", action="store_true", help="Disable progress-bar")

    def get_products(self) -> list[str]:
        response = requests.get("https://endoflife.date/api/all.json", headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()

    def get_product_details(self, product: str) -> list[dict[str, str]]:
        response = requests.get(f"https://endoflife.date/api/{product}.json", headers={"Accept": "application/json"})
        response.raise_for_status()
        return response.json()

    def parse_date(self, details, k):
        if k in details:
            if isinstance(details[k], str):
                try:
                    return timezone.datetime.strptime(details[k], "%Y-%m-%d") if k in details else timezone.datetime.min
                except ValueError:
                    return timezone.datetime.max
            elif not details[k]:
                return timezone.datetime.max
        return timezone.datetime.min

    def handle(self, *args, **options):
        pbar = tqdm(
            self.get_products(), desc="Fetching release cycles for all products", disable=options["no_progress"]
        )
        for product in pbar:
            for cycle in self.get_product_details(product):
                models.EndOfLifeDependency.objects.update_or_create(
                    product=product,
                    cycle=cycle["cycle"],
                    defaults={
                        "release_date": self.parse_date(cycle, "releaseDate"),
                        "latest_release_date": self.parse_date(cycle, "latestReleaseDate"),
                        "eol": self.parse_date(cycle, "eol"),
                        "latest_version": cycle.get("latest", ""),
                        "link": cycle.get("link", "") if cycle.get("link") is not None else "",
                        "lts": self.parse_date(cycle, "lts"),
                        "support": self.parse_date(cycle, "support"),
                        "discontinued": self.parse_date(cycle, "discontinued"),
                    },
                )
                pbar.set_postfix({"product": product})
