from django.db import models

from core_utils.fields import TruncatingCharField


class TruncateFieldModel(models.Model):
    name = models.CharField(max_length=20, null=False, blank=False)
    name_trunc = TruncatingCharField(max_length=10, null=False, blank=False)

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        self.name_trunc = self._meta.get_field('name_trunc').trim_length(self.name_trunc)
        super().save(**kwargs)
