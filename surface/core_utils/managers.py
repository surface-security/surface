from django.db import models


class PrefetchManager(models.Manager):
    def __init__(self, *args, prefetch_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefetch_fields = prefetch_fields or []

    def get_queryset(self):
        return super().get_queryset().prefetch_related(*self._prefetch_fields)
