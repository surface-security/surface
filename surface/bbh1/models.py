from django.db import models
from functools import lru_cache

from simple_history.models import HistoricalRecords


class Scope(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    monitor = models.BooleanField(default=False)
    torify = models.BooleanField(default=False)
    disabled = models.BooleanField(
        default=False,
        help_text="only include in scan if specified explicity (not by wildcards)",
    )
    big_scope = models.BooleanField(default=False, help_text="include even if scope is big")
    scope_domains_in = models.TextField(null=True, blank=True)
    scope_domains_out = models.TextField(null=True, blank=True)
    ignore_domains = models.TextField(
        null=True,
        blank=True,
        help_text="domains that might be discovered but are never processed",
    )

    history = HistoricalRecords()

    def __str__(self) -> str:
        return self.name

    def clean_domains(self, all=False):
        l = self.scope_domains_in or []
        if all:
            l.extend(self.scope_domains_out or [])
        r = []
        for _d in l:
            # some entries will have multiple domains with "," like magisto
            for d in _d.split(","):
                d = d.replace("*.", "").replace("http://", "").replace("https://", "")
                if d[0] == "*":
                    d = d[1:]
                if "*" in d:
                    # still some star, just ignore...
                    continue
                r.append(_d)
        return r

    def ignore_re_check(self, domain):
        for re in self.ignore_re_list:
            if re.match(domain):
                return True
        return False

    @property
    @lru_cache(maxsize=0)
    def ignore_re_list(self):
        import re

        return [re.compile(d) for d in self.ignore_domains or []]
