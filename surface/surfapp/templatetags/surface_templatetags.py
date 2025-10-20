from datetime import timedelta
from urllib.parse import parse_qs

from django import template
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils import timezone
from jsoneditor.forms import JSONEditor

register = template.Library()


@register.simple_tag
def surface_stats(period):
    today = timezone.now()

    if period == "last_24_hours":
        yesterday = today - timedelta(days=1)
        return get_user_model().objects.filter(last_login__gte=yesterday).count()
    elif period == "last_2_weeks":
        two_weeks_ago = today - timedelta(days=14)
        return get_user_model().objects.filter(last_login__gte=two_weeks_ago).count()
    elif period == "total":
        return get_user_model().objects.exclude(last_login=None).count()
    return 0


@register.simple_tag(takes_context=True)
def surface_get_links(context):
    return getattr(settings, "SURFACE_LINKS_ITEMS", None)


@register.filter
def get_query_param(query_string, lookup_kwarg):
    """
    Extracts the value of param_name from a query string.
    Usage: {{ query_string|get_query_param:param_name }}
    """
    if not query_string:
        return ""
    # Remove leading '?' if present
    if query_string.startswith("?"):
        query_string = query_string[1:]
    params = parse_qs(query_string)
    value = params.get(lookup_kwarg)
    if value:
        return value[0]
    return ""


@register.filter
def get_setting_value(setting_name):
    """
    Returns the value of a setting by its name.
    Usage: {{ 'MY_SETTING'|get_setting_value }}
    """
    return getattr(settings, setting_name, None)


# Helpful with templates to see what's in an object
@register.filter
def get_field_content(obj, field):
    try:
        field_name = field.field["name"]
        obj_field = obj._meta.get_field(field_name)

        if obj_field.__class__ is models.JSONField:
            return {
                "type": "json",
                "field": JSONEditor(attrs={"style": "background-color: white !important;"}).render(
                    field_name, getattr(obj, field_name) or [], attrs={"id": f"id_{field_name}"}
                ),
            }

        elif isinstance(obj_field, models.ManyToManyField):
            objects = getattr(obj, field_name)

            urls = []
            for obj in objects.all():
                url = reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
                urls.append({"url": url, "obj": obj})

            return {"type": "urls", "field": urls}

        else:
            return {"type": "field", "field": field}

    except Exception:
        return {"type": "field", "field": field}
