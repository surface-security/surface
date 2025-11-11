import requests
from django.utils import timezone
from tqdm import tqdm

from logbasecommand.base import LogBaseCommand
from sca import models
from sca.utils import create_http_session


class Command(LogBaseCommand):
    help = "Re-sync End Of Life packages from https://endoflife.date"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = create_http_session()
        self.stats = {"products": 0, "cycles": 0, "errors": 0}

    def add_arguments(self, parser):
        parser.add_argument("--no-progress", action="store_true", help="Disable progress-bar")

    def get_products(self) -> list[str]:
        response = self.session.get(
            "https://endoflife.date/api/all.json", headers={"Accept": "application/json"}, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def get_product_details(self, product: str) -> list[dict[str, str]]:
        try:
            response = self.session.get(
                f"https://endoflife.date/api/{product}.json", headers={"Accept": "application/json"}, timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.log_warning(f"Error fetching details for product {product}: {e}")
            self.stats["errors"] += 1
            return []

    def parse_date(self, details, k):
        if k in details:
            if isinstance(details[k], str):
                try:
                    return timezone.datetime.strptime(details[k], "%Y-%m-%d")
                except ValueError:
                    return timezone.datetime.max
            elif not details[k]:
                return timezone.datetime.max
        return timezone.datetime.min

    def handle(self, *args, **options):
        products = self.get_products()
        if not products:
            self.log("No products found.")
            return

        pbar = tqdm(products, desc="Fetching release cycles for all products", disable=options["no_progress"])
        for product in pbar:
            self.stats["products"] += 1
            cycles = self.get_product_details(product)

            if not cycles:
                pbar.set_postfix({"product": product, "status": "skipped"})
                continue

            for cycle in cycles:
                try:
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
                    self.stats["cycles"] += 1
                except (KeyError, ValueError) as e:
                    self.log_warning(f"Error processing cycle for product {product}: {e}")
                    self.stats["errors"] += 1
                    continue

            pbar.set_postfix({"product": product, "cycles": self.stats["cycles"]})

        self.log(
            "Completed: %s products processed, %s cycles synced, %s errors",
            self.stats["products"],
            self.stats["cycles"],
            self.stats["errors"],
        )
