from django.db import models

class Person(models.Model):
    name = models.CharField(max_length=128)


class Application(models.Model):
    tla = models.CharField(max_length=128, blank=True, null=True, db_index=True)  # three/ten letter acronym
    managed_by = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    owned_by = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    director = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    director_direct = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
    dev_lead = models.ForeignKey('Person', blank=True, null=True, on_delete=models.SET_NULL, related_name='+')
