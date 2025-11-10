from functools import lru_cache

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.expressions import Exists
from django.db.models.query_utils import Q

from core_utils.fields import TruncatingCharField
from dns_ips import models as dns_models
from scanners.inputs.base import BaseInput
from scanners.parsers.base import BaseParser


class Rootbox(models.Model):
    name = models.CharField(max_length=255, unique=True)
    active = models.BooleanField(default=True, db_index=True)
    ip = models.CharField(max_length=255)
    ssh_user = models.CharField(max_length=255, null=True, blank=True)
    ssh_port = models.CharField(max_length=255, null=True, blank=True)
    ssh_key = models.CharField(max_length=255, null=True, blank=True)
    dockerd_port = models.IntegerField(default=80, help_text='TCP port to use for dockerd')
    dockerd_tls = models.BooleanField(default=True, help_text='Use TLS with dockerd', verbose_name='Dockerd TLS')
    location = models.CharField(max_length=255, default='')
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def slack_display(self):
        return f'{self.name}, {self.ip} ({self.notes})'

    class Meta:
        verbose_name_plural = 'Rootboxes'
        permissions = (("check_scanners", "Can check scanners"),)


class ScannerImage(models.Model):
    name = models.CharField(max_length=255, primary_key=True)
    image = models.CharField(
        max_length=255, null=False, blank=False, help_text='Full path to image, including registry'
    )
    description = models.TextField(null=True, blank=True)
    vault_secrets = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Scanner Image'
        verbose_name_plural = 'Scanner Images'

    def __str__(self):
        return self.name


class FakeChoicesCharField(models.CharField):
    """
    Field to workaround the lack of "soft" choices in Django.

    Highly unstable, not documented anywhere, picked from random debugging of migration
    system, no real impact assessed!
    TO BE SEEN if no issues come from using this :)
    """

    def deconstruct(self):
        x = super().deconstruct()
        x[3].pop('choices', None)
        return x


class Scanner(models.Model):
    image = models.ForeignKey('ScannerImage', blank=True, on_delete=models.CASCADE)
    docker_tag = models.CharField(max_length=50, default='latest', help_text='Not sure? Use latest')
    rootbox = models.ForeignKey('Rootbox', blank=True, null=True, on_delete=models.CASCADE)
    continous_running = models.BooleanField(default=False, db_index=True)
    scanner_name = models.CharField(max_length=255, unique=True)
    input = FakeChoicesCharField(null=True, blank=True, choices=BaseInput.CHOICES, max_length=30, db_index=True)
    parser = FakeChoicesCharField(null=True, blank=True, choices=BaseParser.CHOICES, max_length=20, db_index=True)
    extra_args = models.CharField(null=True, blank=True, max_length=255)
    environment_vars = models.TextField(
        null=True, blank=True, help_text='Environment variables in json format to be passed to ansible.'
    )
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.scanner_name


class ScanLog(models.Model):
    class States(models.IntegerChoices):
        # from https://docs.docker.com/engine/api/v1.41/#operation/ContainerList
        CREATED = 1
        RESTARTING = 2
        RUNNING = 3
        REMOVING = 4
        PAUSED = 5
        EXITED = 6
        DEAD = 7

    name = models.CharField(max_length=128, unique=True, db_index=True)
    scanner = models.ForeignKey('scanners.Scanner', blank=True, null=True, on_delete=models.SET_NULL)
    rootbox = models.ForeignKey('scanners.Rootbox', blank=True, null=True, on_delete=models.SET_NULL)
    first_seen = models.DateTimeField(null=True, auto_now_add=True, editable=False, db_index=True)
    last_seen = models.DateTimeField(null=True, auto_now=True, editable=False, db_index=True)
    state = models.IntegerField(null=True, blank=True, choices=States.choices, db_index=True)
    exit_code = models.IntegerField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.name


class ScanOutput(models.Model):
    log = models.ForeignKey('ScanLog', on_delete=models.CASCADE, related_name='output_lines')
    # index on timestamp alone might be useful to check all scanners within a timeframe
    timestamp = models.DateTimeField(db_index=True)
    line = models.TextField()

    def __str__(self):
        # do not use log.name to avoid second query
        return str(self.log_id)

    class Meta:
        indexes = [
            # index timestamp with log, as queries will be for a specific ScanLog/container
            models.Index(fields=['log', 'timestamp']),
        ]


class ScanResult(models.Model):
    active = models.BooleanField(default=True, db_index=True)
    first_seen = models.DateTimeField(null=True, auto_now_add=True, editable=False, db_index=True)
    last_seen = models.DateTimeField(null=True, auto_now=True, editable=False, db_index=True)
    scanner = models.ForeignKey('scanners.Scanner', blank=True, null=True, on_delete=models.SET_NULL)
    rootbox = models.ForeignKey('scanners.Rootbox', blank=True, null=True, on_delete=models.SET_NULL)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        abstract = True


class LiveHostQS(models.QuerySet):
    """
    This queryset implements the ability to query on the GenericFK ("host") the same way (more or less)
    as it is possible to query on normal FK, eg:
    .filter(host__record__name="betfair.com")

    If the attribute is common to any of the ContentTypes supported
    (currently IPAddress and DNSRecord), it can also be filtered using "any", eg:
    .filter(host__any__name="betfair.com")
    """

    INVALID_VALUE = object()

    def __init__(self, *a, **b):
        super().__init__(*a, **b)
        # TODO: get GenericFK fields from model definition / self.model
        self.__allowed_cts = {
            'ip': (dns_models.IPAddress,),
            'record': (dns_models.DNSRecord,),
            'any': (dns_models.DNSRecord, dns_models.IPAddress),
        }
        # validator that will choose whether or not to include this CT for a given value
        # this prevents db backend errors such as sending hostnames using `any` on Postgres
        # (where IPAddress fields are cast to ::inet)
        self.__validators = {
            dns_models.IPAddress: self._valid_ip_fields,
        }

    @classmethod
    @lru_cache
    def valid_ip_re(cls):
        import re

        return re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(\/\d{1,2})?$')

    @classmethod
    def valid_ip(cls, value):
        return cls.valid_ip_re().match(value) is not None

    def _valid_ip_fields(self, parts, value):
        if not parts or parts[0] != 'name':
            return value
        # TODO: lookups can be anything/custom, meaning value might be anything as well...
        # how to handle this? or just drop all this LiveHostQS....
        if len(parts) > 1 and parts[1] == 'in':
            res = {x for x in value if self.valid_ip(x)} or self.INVALID_VALUE
        else:
            res = value if self.valid_ip(value) else self.INVALID_VALUE
        return res

    def _filter_or_exclude_gfk_models(self, keyword):
        # TODO: to support configurable/allowed ContentTypes
        if keyword not in self.__allowed_cts:
            raise ValueError(f'{keyword} is not valid ContentType for host GenericForeignKey')
        return self.__allowed_cts[keyword]

    def _filter_or_exclude_q_tuple(self, q_tuple):
        # inherent assert len == 2
        field, value = q_tuple
        if field == 'host':
            return (
                Q(
                    host_content_type=ContentType.objects.get_for_model(value),
                    host_object_id=value.pk,
                ),
                True,
            )
        if field.startswith('host__'):
            parts = field.split('__')
            combined_q = Q()
            for model in self._filter_or_exclude_gfk_models(parts[1]):
                if model in self.__validators:
                    new_value = self.__validators[model](parts[2:], value)
                    if new_value == self.INVALID_VALUE:
                        continue
                qkwargs = {}
                qkwargs['host_content_type'] = ContentType.objects.get_for_model(model)
                if len(parts) == 2:
                    # exact record match, same as host but with forced ContentType check
                    qkwargs['host_object_id'] = value.pk if hasattr(value, 'pk') else value
                else:
                    att = '__'.join(parts[2:])
                    # TODO: group all host__CT together to put in the same filter()
                    qkwargs['host_object_id__in'] = model.objects.filter(**{att: value})
                combined_q |= models.Q(**qkwargs)
            if not combined_q:
                # if Q() is still empty, it means no valid values were passed, so nothing should be returned!
                # TODO: is there a Q() that results in .none() being called (ie: no DB query)? handle it higher for now
                raise ValueError(-1, 'all filters invalid')
            return combined_q, True
        return q_tuple, False

    def _filter_or_exclude_q_obj(self, q_obj):
        if isinstance(q_obj, tuple):
            # tuple is the actual condition, handle it!
            # can it be more field/value tuple? assert for now, fix later if needed
            assert len(q_obj) == 2
            q_obj, _ = self._filter_or_exclude_q_tuple(q_obj)
        else:
            # is there anything else that should be supported? assert for now

            if isinstance(q_obj, Exists):
                return q_obj
            assert isinstance(q_obj, Q)
            for ind, child in enumerate(q_obj.children):
                q_obj.children[ind] = self._filter_or_exclude_q_obj(child)
        return q_obj

    def _filter_or_exclude_args(self, args):
        args = [self._filter_or_exclude_q_obj(arg) for arg in args]
        return args

    def _filter_or_exclude(self, negate, args, kwargs):
        # TODO: properly handle/merge multiple host__ kwargs...
        # also handle contentypes dynamically.. (based on limit_choices from model?)

        try:
            args = self._filter_or_exclude_args(args)
            to_remove = set()
            for k, v in kwargs.items():
                q, c = self._filter_or_exclude_q_tuple((k, v))
                if c:
                    # do not modify kwargs inside loop
                    to_remove.add(k)
                    args.append(q)
            for k in to_remove:
                kwargs.pop(k)
            return super()._filter_or_exclude(negate, args, kwargs)
        except ValueError as e:
            if e.args == (-1, 'all filters invalid'):
                # crappy check... to be removed, once Q() .none equivalent is found
                return super().none()
            raise


class LiveHostManager(models.Manager):
    # TODO: make the queryset helper methods dynamic (based on LIMIT_CHOICES?)
    # TODO: find solution for "select_related"... use prefetch_related until then...
    # TODO: how to make this queryset/manager used as RelatedManager (in other models)??

    def __init__(self, limit_choices):
        super().__init__()
        self.__cts = []
        for m in limit_choices:
            if isinstance(m, models.base.ModelBase):
                self.__cts.append((m._meta.app_label, m._meta.model_name))
            elif isinstance(m, str):
                parts = m.lower().split('.')
                assert len(parts) == 2
                self.__cts.append(tuple(parts))
            elif isinstance(m, tuple):
                assert len(m) == 2
                self.__cts.append(m)

    def get_queryset(self):
        return LiveHostQS(model=self.model, using=self._db)

    def limit_choices(self):
        if not self.__cts:
            raise ValueError('invalid choices')
        first_ct = self.__cts[0]
        q = models.Q(app_label=first_ct[0], model=first_ct[1])
        for ct in self.__cts[1:]:
            q |= models.Q(app_label=ct[0], model=ct[1])
        return q


class CustomGFK(GenericForeignKey):
    def get_lookup(self, *a, **b):
        # FIXME: should the QS logic be moved into custom lookups?
        # custom queryset solves admin direct search results on LiveHost but
        # what about RelatedManager, can lookups solve it?
        return None


class LiveHost(ScanResult):
    objects = LiveHostManager([dns_models.DNSRecord, dns_models.IPAddress])

    host_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, limit_choices_to=objects.limit_choices()
    )
    host_object_id = models.PositiveIntegerField()
    host = CustomGFK('host_content_type', 'host_object_id')
    port = models.IntegerField(default=443)
    status_code = models.IntegerField(null=True)
    final_url = TruncatingCharField(max_length=1024, null=True, blank=True)
    body_response = models.TextField(null=True, blank=True)
    timing = models.CharField(max_length=128, null=True, blank=True)
    redirects = models.TextField(null=True, blank=True)
    third_party = models.BooleanField(default=False)
    headers = models.TextField(null=True, blank=True)
    cookies = models.TextField(null=True, blank=True)
    technologies = models.ManyToManyField('Technology')

    def save(self, *args, **kwargs):
        self.final_url = self._meta.get_field('final_url').trim_length(self.final_url)
        self.third_party = self.is_third_party()
        super().save(*args, **kwargs)

    def is_third_party(self):
        if hasattr(self.host, 'tags'):
            # inneficient but only used by save()...? "third_party" flagging needs review/refactor
            return self.host.tags.filter(name='is_third_party').exists()
        return False

    def __str__(self):
        if self.host:
            if self.port == 80:
                return f'http://{self.host.name}'
            elif self.port == 443:
                return f'https://{self.host.name}'
            return f'{self.host.name}:{self.port}'
        return f'{self.host_object_id}/{self.host_content_type_id}:{self.port}'

    class Meta:
        verbose_name = 'Scanner Result - Live Host'
        verbose_name_plural = 'Scanner Results - Live Hosts'
        unique_together = [('host_content_type', 'host_object_id', 'port')]


class Technology(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class TechUsedResult(ScanResult):
    host = models.ForeignKey('LiveHost', on_delete=models.CASCADE)
    application = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    version = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    confidence = models.IntegerField(blank=True, null=True, db_index=True)

    class Meta:
        verbose_name = 'Scanner Result - Tech Used'
        verbose_name_plural = 'Scanner Results - Tech Used'
        unique_together = (('host', 'application'),)


class RawResult(ScanResult):
    file_name = models.CharField(max_length=255, null=True, blank=True)
    raw_results = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Scanner Result - Raw'
        verbose_name_plural = 'Scanner Results - Raw'

    def __str__(self):
        return str(self.last_seen)
