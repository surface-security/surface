import datetime
from urllib.parse import urlencode
import operator
import pytz

from django.contrib.admin.filters import RelatedFieldListFilter
from django.contrib.admin.options import ModelAdmin
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.core.handlers.wsgi import WSGIRequest
from django.contrib.admin.filters import RelatedFieldListFilter
from django.contrib.admin.options import ModelAdmin
from django.core.handlers.wsgi import WSGIRequest
from django.db.models.base import Model
from django.db.models.fields import BLANK_CHOICE_DASH, Field
from django.db.models.fields.related import RelatedField
from django.contrib import admin
from django.shortcuts import redirect
from django.utils import timezone
from django.conf import settings
from django import forms
from django.contrib.admin.widgets import AdminDateWidget

try:
    from theme.filters import DateRangeFilter as OriginalDateRangeFilter

    class CalendarFilter(OriginalDateRangeFilter):
        def __init__(self, field, request, params, model, model_admin, field_path):
            self.lookup_kwarg_within = f'{field_path}__within'
            super().__init__(field, request, params, model, model_admin, field_path)

        def _get_form_fields(self):
            return {
                self.lookup_kwarg_within: forms.DateField(
                    label='',
                    widget=AdminDateWidget(attrs={'placeholder': self.field_path.replace("_", " ").title()}),
                    localize=True,
                    required=False,
                )
            }

        def _get_expected_fields(self):
            return [self.lookup_kwarg_within]

        def _make_query_filter(self, request, validated_data):
            query_params = {}
            date_value = validated_data.get(self.lookup_kwarg_within, None)

            if date_value:
                date_gte = self.make_dt_aware(
                    datetime.datetime.combine(date_value, datetime.time.min), self.get_timezone(request)
                )
                query_params[f'{self.field_path}__gte'] = date_gte
                query_params[f'{self.field_path}__lt'] = date_gte + datetime.timedelta(days=1)

            return query_params

        def get_timezone(self, request):
            return timezone.get_default_timezone()

        @staticmethod
        def make_dt_aware(value, timezone):
            if settings.USE_TZ and pytz is not None:
                default_tz = timezone
                if value.tzinfo is not None:
                    value = default_tz.normalize(value)
                else:
                    value = default_tz.localize(value)
            return value

except ImportError:
    pass


class SelectRelatedFilter(RelatedFieldListFilter):
    def __init__(
        self,
        field: Field,
        request: WSGIRequest,
        params: dict[str, str],
        model: type[Model],
        model_admin: ModelAdmin,
        field_path: str,
    ) -> None:
        # validate select_related is defined now for early errors
        if not hasattr(model_admin, 'list_filter_select_related'):
            raise ImproperlyConfigured(
                "The list filter '%s' requires '%s' to define 'list_filter_select_related'."
                % (
                    self.__class__.__name__,
                    model_admin.__class__.__name__,
                )
            )
        if field.name not in model_admin.list_filter_select_related:
            raise ImproperlyConfigured(
                "The list filter '%s' '%s.list_filter_select_related' is not set for field '%s'."
                % (
                    self.__class__.__name__,
                    model_admin.__class__.__name__,
                    field.name,
                )
            )
        super().__init__(field, request, params, model, model_admin, field_path)

    def _custom_field_get_choices(
        self, field, include_blank=True, blank_choice=BLANK_CHOICE_DASH, limit_choices_to=None, ordering=()
    ):
        """
        copy from django.db.models.fields.related.RelatedField.get_choices
        only change was returning "qs" at the end instead of the stringified options
        (and replacing "self" per "field" obviously)
        """
        if field.choices is not None:
            choices = list(field.choices)
            if include_blank:
                blank_defined = any(choice in ('', None) for choice, _ in field.flatchoices)
                if not blank_defined:
                    choices = blank_choice + choices
            return choices
        rel_model = field.remote_field.model
        limit_choices_to = limit_choices_to or field.get_limit_choices_to()
        qs = rel_model._default_manager.complex_filter(limit_choices_to)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def field_choices(
        self, field: RelatedField, request: WSGIRequest, model_admin: ModelAdmin
    ) -> list[tuple[str, str]]:
        # re-implement Field get_choices as it doesn't return the queryset itself, but the strings already built...
        ordering = self.field_admin_ordering(field, request, model_admin)
        choice_func = operator.attrgetter(
            field.remote_field.get_related_field().attname if hasattr(field.remote_field, 'get_related_field') else 'pk'
        )
        qs = self._custom_field_get_choices(field, include_blank=False, ordering=ordering).select_related(
            *model_admin.list_filter_select_related[field.name]
        )
        return [(choice_func(x), str(x)) for x in qs]


class DefaultFilterMixin:
    """Source:
    https://medium.com/@hakibenita/things-you-must-know-about-django-admin-as-your-app-gets-bigger-6be0b0ee9614
    """

    def get_default_filters(self, request):
        """Set default filters to the page.
        request (Request)
        Returns (dict):
            Default filter to encode.
        """
        raise NotImplementedError()

    def changelist_view(self, request, extra_context=None):
        ref = request.META.get('HTTP_REFERER', '')
        path = request.META.get('PATH_INFO', '')
        # if any existing GET parameters, do not apply default filters
        # if referrer comes from changelist itself (or an action such as /add/), do not apply default filters
        if request.GET or path in ref:
            return super().changelist_view(request, extra_context=extra_context)
        query = urlencode(self.get_default_filters(request))
        return redirect(f'{path}?{query}')


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper
