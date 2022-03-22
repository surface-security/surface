from django.db import models


class PrefetchManager(models.Manager):
    def __init__(self, *args, prefetch_fields=None, select_related_fields=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._prefetch_fields = prefetch_fields
        self._select_related_fields = select_related_fields

    def get_queryset(self):
        q = super().get_queryset()
        if self._prefetch_fields:
            q = q.prefetch_related(*self._prefetch_fields)
        if self._select_related_fields:
            q = q.select_related(*self._select_related_fields)
        return q
