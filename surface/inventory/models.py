from django.contrib.contenttypes import models as ct_models
from django.db import models
from fernet_fields import EncryptedTextField


class Person(models.Model):
    name = models.CharField(max_length=128)


class Integration(models.Model):
    content_source = models.ForeignKey(ct_models.ContentType, on_delete=models.CASCADE)

    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    actions = models.JSONField(null=False, blank=False)
    secrets = EncryptedTextField(null=True, blank=False)
    enabled = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs):
        if 'content_source' not in kwargs:
            kwargs['content_source'] = self.content_type()
        super().__init__(*args, **kwargs)

    @classmethod
    def content_type(cls):
        return ct_models.ContentType.objects.get_for_model(cls)

    @property
    def cached_content_source(self):
        if self.content_source_id is not None and not Integration.content_source.is_cached(self):
            self.content_source = ct_models.ContentType.objects.get_for_id(self.content_source_id)
        return self.content_source

    def __str__(self):
        return f'{self.pk} [{self.cached_content_source.app_label}] - {self.title}'


class Application(models.Model):
    tla = models.CharField(max_length=128, blank=True, null=True, db_index=True)  # three/ten letter acronym
    managed_by = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    owned_by = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    director = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    director_direct = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    dev_lead = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
