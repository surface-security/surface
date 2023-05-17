from django.contrib.contenttypes import models as ct_models
from django.db import models


class FindingInheritanceQS(models.QuerySet):
    def get_children(self) -> list:
        return [
            getattr(m, m.content_source.model)
            for m in self.prefetch_related("content_source__model__finding_ptr").select_related('content_source')
        ]


class Finding(models.Model):
    class Severity(models.IntegerChoices):
        INFORMATIVE = 1
        LOW = 2
        MEDIUM = 3
        HIGH = 4
        CRITICAL = 5

    class State(models.IntegerChoices):
        """
        States represent a point in the workflow.
        States are not Status.
        Do not add a state if the transitions for that state are the same as an existing one.

        mermaid flowchart (https://mermaid.live/)
        flowchart TD
          NEW -->|valid, assigned for resolution| OPEN
          NEW -->|invalid, false positive or known accepted risk | CLOSED
          OPEN -->|resolved| RESOLVED
          RESOLVED -->|regression| NEW
        """

        NEW = 1
        OPEN = 2
        CLOSED = 3
        RESOLVED = 4

    content_source = models.ForeignKey(ct_models.ContentType, on_delete=models.CASCADE, related_name="content_source")

    title = models.TextField(blank=True)
    summary = models.TextField(null=True, blank=True)
    severity = models.IntegerField(null=True, blank=True, choices=Severity.choices, db_index=True)
    state = models.IntegerField(choices=State.choices, default=State.NEW, db_index=True)

    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen_date = models.DateTimeField(blank=True, null=True)

    application = models.ForeignKey(
        'inventory.Application',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Application",
        related_name="application",
    )

    related_to = models.ManyToManyField('self', blank=True, help_text='Other findings related to this one')

    objects = FindingInheritanceQS.as_manager()

    def __init__(self, *args, **kwargs):
        if 'content_source' not in kwargs:
            kwargs['content_source'] = self.content_type()
        super().__init__(*args, **kwargs)

    @classmethod
    def content_type(cls):
        return ct_models.ContentType.objects.get_for_model(cls)

    @property
    def cached_content_source(self):
        if self.content_source_id is not None and not Finding.content_source.is_cached(self):
            self.content_source = ct_models.ContentType.objects.get_for_id(self.content_source_id)
        return self.content_source

    def __str__(self):
        return f'{self.pk} [{self.cached_content_source.app_label}] - {self.title}'
