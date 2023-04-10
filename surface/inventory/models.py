from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=128)


class Integration(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    actions = models.JSONField(null=False, blank=False)
    enabled = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Application(models.Model):
    tla = models.CharField(max_length=128, blank=True, null=True, db_index=True)  # three/ten letter acronym
    managed_by = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    owned_by = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    director = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    director_direct = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    dev_lead = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
