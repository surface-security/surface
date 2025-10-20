import datetime
from collections import OrderedDict
from typing import Any
from urllib.parse import urlencode

from django import forms
from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.widgets import AdminDateWidget
from django.core.validators import EMPTY_VALUES
from django.db.models import Model, QuerySet
from django.db.models.base import Model
from django.db.models.fields import Field
from django.forms import ValidationError
from django.http import HttpRequest
from django.shortcuts import redirect
from rangefilter.filter import DateRangeFilter as OriginalDateRangeFilter
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import DropdownFilter as UnfoldDropdownFilter
from unfold.contrib.filters.admin.dropdown_filters import RelatedDropdownFilter
from unfold.contrib.filters.admin.mixins import AutocompleteMixin
from unfold.contrib.filters.forms import AutocompleteDropdownForm, DropdownForm
from unfold.utils import parse_date_str
from unfold.widgets import INPUT_CLASSES


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
        ref = request.META.get("HTTP_REFERER", "")
        path = request.META.get("PATH_INFO", "")
        # if any existing GET parameters, do not apply default filters
        # if referrer comes from changelist itself (or an action such as /add/), do not apply default filters
        if request.GET or path in ref:
            return super().changelist_view(request, extra_context=extra_context)
        query = urlencode(self.get_default_filters(request))
        return redirect(f"{path}?{query}")


def custom_titled_filter(title):
    class Wrapper(admin.FieldListFilter):
        def __new__(cls, *args, **kwargs):
            instance = admin.FieldListFilter.create(*args, **kwargs)
            instance.title = title
            return instance

    return Wrapper


class DateForm(forms.Form):
    class Media:
        js = [
            "admin/js/calendar.js",
            "unfold/filters/js/DateTimeShortcuts.js",
        ]

    def __init__(self, name: str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.name = name
        # Ensure the filter value is always a string, not a list
        key = f"{name}__within"
        if hasattr(self, "data") and self.data.get(key):
            val = self.data.get(key)
            if isinstance(val, list):
                # Take the first value if it's a list
                data = self.data.copy()
                data[key] = val[0] if val else ""
                self.data = data
        # Normalize '0' to empty string for the filter value
        if hasattr(self, "data") and self.data.get(key) == "0":
            data = self.data.copy()
            data[key] = ""
            self.data = data
        self.fields[key] = forms.DateField(
            label="",
            required=False,
            widget=forms.DateInput(
                attrs={
                    "placeholder": "Select date",
                    "class": f"vCustomDateField {' '.join(INPUT_CLASSES)}",
                }
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        # Ensure '0' is treated as empty
        key = f"{self.name}__within"
        if cleaned_data.get(key) == "0":
            cleaned_data[key] = None
        return cleaned_data


class CalendarFilter(admin.FieldListFilter):
    form_class = DateForm
    request = None
    parameter_name = None
    template = "unfold/filters/filters_date_range.html"

    def __init__(
        self,
        field: Field,
        request: HttpRequest,
        params: dict[str, str],
        model: type[Model],
        model_admin: ModelAdmin,
        field_path: str,
    ) -> None:
        super().__init__(field, request, params, model, model_admin, field_path)
        self.request = request
        if self.parameter_name is None:
            self.parameter_name = self.field_path

        if self.parameter_name + "__within" in params:
            value = params.pop(self.field_path + "__within")
            value = value[0] if isinstance(value, list) else value

            if value not in EMPTY_VALUES:
                self.used_parameters[self.field_path + "__within"] = value

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        filters = {}

        value_within = self.used_parameters.get(self.parameter_name + "__within")
        if value_within not in EMPTY_VALUES:
            filters.update({"last_seen__lt": parse_date_str(value_within) + datetime.timedelta(days=1)})
            filters.update({"first_seen__gte": parse_date_str(value_within)})

        try:
            return queryset.filter(**filters)
        except (ValueError, ValidationError):
            return None

    def expected_parameters(self) -> list[str]:
        return [
            f"{self.parameter_name}__within",
        ]

    def choices(self, changelist: ChangeList) -> tuple[dict[str, Any], ...]:
        parameter_name = self.parameter_name or ""
        value = self.used_parameters.get(f"{parameter_name}__within", None)
        # Normalize value to a string if it's a list
        if isinstance(value, list):
            value = value[0] if value else None
        # If value is "0", use current date in YYYY-MM-DD format
        if value == "0":
            value = datetime.date.today().strftime("%Y-%m-%d")
        return (
            {
                "request": self.request,
                "parameter_name": parameter_name,
                "form": self.form_class(
                    name=str(parameter_name),
                    data={
                        f"{parameter_name}__within": value,
                    },
                ),
            },
        )


class customAutocompleteDropdownForm(AutocompleteDropdownForm):
    class Media:
        js = ()
        css = {}


class AutocompleteSelectFilter(AutocompleteMixin, RelatedDropdownFilter):
    form_class = customAutocompleteDropdownForm


class RelatedFieldAjaxListFilter(AutocompleteSelectFilter):
    pass


class CustomDropdownForm(DropdownForm):
    class Media:
        js = ()
        css = {}


class DropdownFilter(UnfoldDropdownFilter):
    form_class = CustomDropdownForm


class DateRangeFilter(OriginalDateRangeFilter):
    def get_template(self):
        return "rangefilter/date_filter.html"

    def _get_form_fields(self):
        # this is here, because in parent DateRangeFilter AdminDateWidget
        # could be imported from django-suit
        return OrderedDict(
            (
                (
                    self.lookup_kwarg_gte,
                    forms.DateField(
                        label="",
                        widget=AdminDateWidget(attrs={"placeholder": "From date"}),
                        localize=True,
                        required=False,
                    ),
                ),
                (
                    self.lookup_kwarg_lte,
                    forms.DateField(
                        label="",
                        widget=AdminDateWidget(attrs={"placeholder": "To date"}),
                        localize=True,
                        required=False,
                    ),
                ),
            )
        )
