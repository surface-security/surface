import netaddr
from django.conf import settings
from django.core import exceptions, validators
from django.db import models
from django.db.models import fields


class UnsignedIntegerField(fields.IntegerField):
    validators = [validators.MinValueValidator(0), validators.MaxValueValidator(4294967296)]

    def db_type(self, connection=None):
        # connection not used, types hardcoded
        if settings.DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
            return "integer UNSIGNED"
        if settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
            return "integer"
        if settings.DATABASES["default"]["ENGINE"] in (
            "django.db.backends.postgresql_psycopg2",
            "django.db.backends.postgresql",
        ):
            return "bigint"
        raise NotImplementedError(settings.DATABASES["default"]["ENGINE"])

    def get_internal_type(self):
        return "PositiveIntegerField"

    def to_python(self, value):
        if value is None:
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError("This value must be an unsigned integer.")


class RangeModel(models.Model):
    range = models.CharField(max_length=100)
    range_min = UnsignedIntegerField(null=True, blank=True)
    range_max = UnsignedIntegerField(null=True, blank=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        try:
            if "-" in self.range:
                first, second = self.range.split("-")
                _x = netaddr.IPRange(first, second)
            else:
                _x = netaddr.IPNetwork(self.range)
            self.range_min = _x.first
            self.range_max = _x.last
        except Exception:
            self.range_min = None
            self.range_max = None
        return super().save(force_insert, force_update, using, update_fields)

    class Meta:
        abstract = True


class TruncatingCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        self._dotdotdot = kwargs.pop("dotdotdot", True)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self.trim_length(value)

    def trim_length(self, value):
        if value and len(value) > self.max_length:
            return value[: self.max_length - 3] + "..."
        return value
