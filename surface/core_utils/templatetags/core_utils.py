from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def admin_reverse(context, obj, action="change"):
    """Reverse admin url for given object"""
    # crappy admin_urlname tag is useless as it requires meta model to be passed as first parameter...
    if not obj:
        return None

    if action in ["change"]:
        args = (obj.pk,)
    else:
        args = None

    return context.request.build_absolute_uri(
        reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_{action}", args=args)
    )


@register.filter
def verbose_name(obj):
    return obj._meta.verbose_name
