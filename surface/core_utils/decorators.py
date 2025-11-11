import time
from functools import lru_cache, wraps

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.utils import model_ngettext
from django.http.response import HttpResponseForbidden
from django.template import defaultfilters, response
from django.urls import reverse
from django.utils.html import format_html, mark_safe


def lru_cache_time(seconds, maxsize=None):
    """
    Adds time aware caching to lru_cache
    source: https://stackoverflow.com/a/57300326

    Notice this does not invalidate cache X seconds after *first use* but instead invalidates it
    every X seconds. If first use was between windows, it will be invalidated sooner.
    It shouldn't be a big issue
    """

    def wrapper(func):
        @lru_cache(maxsize=maxsize)
        def time_aware(__ttl, *args, **kwargs):
            """
            Main wrapper, note that the first argument ttl is not passed down.
            This is because no function should bother to know this that
            this is here.
            """
            return func(*args, **kwargs)

        @wraps(func)
        def wrapping(*args, **kwargs):
            return time_aware(int(time.time() / seconds), *args, **kwargs)

        return wrapping

    return wrapper


def mark_safe_display(attr, column_name=None):
    """
    Helper to be able to mark_safe directly in list_display
    """
    if column_name is None:
        # like django.db.models.Field does
        column_name = attr.replace("_", " ")

    def _get_attr(obj):
        r = getattr(obj, attr)
        if r is not None:
            return mark_safe(r)

    _get_attr.short_description = column_name
    _get_attr.admin_order_field = attr
    return _get_attr


def linebreaks_display(attr, column_name=None):
    """
    Helper to be able to linebreaksbr directly in list_display
    """
    if column_name is None:
        # like django.db.models.Field does
        column_name = attr.replace("_", " ")

    def _get_attr(obj):
        r = getattr(obj, attr)
        if r is not None:
            return defaultfilters.linebreaksbr(r)

    _get_attr.short_description = column_name
    _get_attr.admin_order_field = attr
    return _get_attr


def admin_change_url(obj, relative=True):
    """Source:
    https://medium.com/@hakibenita/things-you-must-know-about-django-admin-as-your-app-gets-bigger-6be0b0ee9614
    """
    # TODO replace with django contrib admin admin_urls template tag... does the same...
    app_label = obj._meta.app_label
    model_name = obj._meta.model_name
    return ("" if relative else settings.BASE_HOSTNAME) + reverse(
        f"admin:{app_label}_{model_name}_change", args=(obj.pk,)
    )


def admin_change_link(obj, description, relative=True):
    url = admin_change_url(obj, relative)

    return format_html('<a href="{}">{}</a>', url, description)


def admin_link_helper(attr, column_name=None, description=None, empty_description=None):
    """
    Helper to be able to use admin_link directly in list_display
    """
    if column_name is None:
        # like django.db.models.Field does
        column_name = attr.replace("_", " ")

    def _get_attr(obj):
        related_obj = getattr(obj, attr)
        related_obj_id = getattr(obj, f"{attr}_id")
        if related_obj is None or not related_obj_id:
            return empty_description
        return admin_change_link(related_obj, description or str(related_obj))

    _get_attr.short_description = column_name
    _get_attr.admin_order_field = attr
    return _get_attr


def admin_link(attr, short_description, empty_description="-"):
    """Decorator used for rendering a link to a related model in
    the admin detail page.
    attr (str):
        Name of the related field.
    short_description (str):
        Name if the field.
    empty_description (str):
        Value to display if the related field is None.
    The wrapped method receives the related object and should
    return the link text.
    Usage:
        @admin_link('credit_card', _('Credit Card'))
        def credit_card_link(self, credit_card):
            return credit_card.name
    Source:
        https://medium.com/@hakibenita/things-you-must-know-about-django-admin-as-your-app-gets-bigger-6be0b0ee9614
    """

    def wrap(func):
        def field_func(self, obj):
            related_obj = getattr(obj, attr)
            related_obj_id = getattr(obj, f"{attr}_id")
            if related_obj is None or not related_obj_id:
                return empty_description
            return admin_change_link(related_obj, func(self, related_obj))

        field_func.short_description = short_description
        return field_func

    return wrap


def admin_changelist_url(model, relative=True):
    """Source:
    https://medium.com/@hakibenita/things-you-must-know-about-django-admin-as-your-app-gets-bigger-6be0b0ee9614
    """
    # TODO replace with django contrib admin admin_urls template tag... does the same...
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    return ("" if relative else settings.BASE_HOSTNAME) + reverse(f"admin:{app_label}_{model_name}_changelist")


def admin_changelist_link(attr, short_description, empty_description="-", query_string=None):
    """Decorator used for rendering a link to the list display of
    a related model in the admin detail page.
    attr (str):
        Name of the related field.
    short_description (str):
        Field display name.
    empty_description (str):
        Value to display if the related field is None.
    query_string (function):
        Optional callback for adding a query string to the link.
        Receives the object and should return a query string.
    The wrapped method receives the related object and
    should return the link text.
    Usage:
        @admin_changelist_link('credit_card', _('Credit Card'))
        def credit_card_link(self, credit_card):
            return credit_card.name
    Source:
        https://medium.com/@hakibenita/things-you-must-know-about-django-admin-as-your-app-gets-bigger-6be0b0ee9614
    """

    def wrap(func):
        def field_func(self, obj):
            related_obj = getattr(obj, attr)
            if related_obj is None:
                return empty_description
            url = admin_changelist_url(related_obj.model)
            if query_string:
                url += "?" + query_string(obj)
            return format_html('<a href="{}">{}</a>', url, func(self, related_obj))

        field_func.short_description = short_description
        field_func.allow_tags = True
        return field_func

    return wrap


def require_api_token(token=None):
    """Decorator used for protecting a view with a token
    token (str):
        Actual required token, defaults to settings.API_TOKEN
    Usage:
        @require_api_token
        def api_view(request):
            return private_eyes_only
    """
    if callable(token) or token is None:
        _token = settings.API_TOKEN
    else:
        _token = token

    def wrap(func):
        def wrapped_func(request, *args, **kwargs):
            inp_token = request.GET.get("token") or request.POST.get("token")
            if inp_token != _token:
                return HttpResponseForbidden()
            return func(request, *args, **kwargs)

        return wrapped_func

    if callable(token):
        # not really the token, just a call without ()!
        return wrap(token)
    else:
        return wrap


def confirm_action(template=None, title="Are you sure?", short_description=None):
    """
    Decorator used for ModelAdmin actions that require a confirmation page.
    template:
        Template to use. If None, the usual admin template lookup paths
        (global, per app, per model) are used. If choosing one custom, check
        admin/custom_action_confirmation.html to see existing blocks or
        re-defined entirely.
    title:
        The <title> to be used in the page
    short_description:
        This will be used by the default template as in
        "Are you sure you want to <SHORT_DESCRIPTION> for the following..."
        This defaults to action method short_description.
    The wrapped method should just do the action as if it was already confirmed.
    Usage:
        @confirm_action
        def custom_delete(self, request, queryset):
            return queryset.update(logical_delete=True)
        custom_delete.short_description = 'Disable objects'
        custom_delete.allowed_permissions = ('change',)
    """

    func = None
    if template is not None and callable(template):
        # decorator used without (), template is the decorated function
        func = template
        template = None

    def _callable(func):
        @wraps(func)
        def _confirm_first(model_admin, request, queryset):
            # based on delete_selected action
            # https://github.com/django/django/blob/ca9872905559026af82000e46cde6f7dedc897b6/django/contrib/admin/actions.py#L28

            # The user has already confirmed the action.
            # Just Do It
            if request.POST.get("post"):
                return func(model_admin, request, queryset)

            short_description_in_use = (
                short_description
                or getattr(func.__wrapper, "short_description", func.__name__.replace("_", " ")).lower()
            )

            opts = model_admin.model._meta
            app_label = opts.app_label
            context = {
                **model_admin.admin_site.each_context(request),
                "title": title,
                "objects_name": str(model_ngettext(queryset)),
                "queryset": queryset,
                "opts": opts,
                "action": request.POST.get("action"),
                "action_short_description": short_description_in_use,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                "media": model_admin.media,
            }

            request.current_app = model_admin.admin_site.name

            # Display the confirmation page
            return response.TemplateResponse(
                request,
                template
                or [
                    "admin/%s/%s/custom_action_confirmation.html" % (app_label, opts.model_name),
                    "admin/%s/custom_action_confirmation.html" % app_label,
                    "admin/custom_action_confirmation.html",
                ],
                context,
            )

        # short_description is set to the action method *after* it is wrapped
        # preserve reference to wrapper so we retrieve it later
        func.__wrapper = _confirm_first
        return _confirm_first

    return _callable(func) if func else _callable


def relatedobj_field(attr, attr_field, description=None):
    """
    Helper to wrap relatedfield fields in list_display
    """

    def _get_attr(obj):
        related_obj = getattr(obj, attr)
        if related_obj:
            return getattr(related_obj, attr_field)

    _get_attr.short_description = description  # TODO get attr_field verbose_name somehow?
    _get_attr.admin_order_field = f"{attr}__{attr_field}"
    return _get_attr
