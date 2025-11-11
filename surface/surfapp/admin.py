from django.contrib import admin
from django.contrib.admin import site
from django.contrib.auth import admin as AuthAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db.migrations.recorder import MigrationRecorder
from django.utils.html import format_html
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from apitokens.admin import MyTokenAdmin, TokenAdmin
from apitokens.models import MyToken, Token
from core_utils.admin import DefaultModelAdmin
from core_utils.admin_filters import DropdownFilter
from dbcleanup import utils as dbcleanup_utils
from dbcleanup.admin import TableAdmin
from dbcleanup.models import Table
from dkron import utils
from dkron.admin import JobAdmin
from dkron.models import Job
from impersonate.admin import impersonate_action
from notifications.admin import EventAdmin, SubscriptionAdmin
from notifications.models import Event, Subscription

AuthAdmin.UserAdmin.actions = AuthAdmin.UserAdmin.actions + (impersonate_action,)

site.site_title = "Surface"
site.site_url = "https://github.com/surface-security/surface"
site.index_title = "Home"


# User Admin Patch
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, DefaultModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


# Group Admin Patch
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, DefaultModelAdmin):
    pass


@admin.register(MigrationRecorder.Migration)  # noqa: F405
class MigrationAdmin(DefaultModelAdmin):  # noqa: F405
    list_display = ("app", "name", "applied")
    search_fields = ("app", "name")
    list_filter = ("app",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Notifications Admin patch
admin.site.unregister(Event)


@admin.register(Event)
class EventAdminAdmin(EventAdmin, DefaultModelAdmin):
    pass


admin.site.unregister(Subscription)


@admin.register(Subscription)
class SubscriptionAdmin(SubscriptionAdmin, DefaultModelAdmin):
    pass


# Token Admin Patch
admin.site.unregister(Token)


@admin.register(Token)
class TokenAdmin(TokenAdmin, DefaultModelAdmin):
    pass


admin.site.unregister(MyToken)


@admin.register(MyToken)
class MyTokenAdmin(MyTokenAdmin, DefaultModelAdmin):
    pass


# DKron Job Admin Patch
admin.site.unregister(Job)


@admin.register(Job)
class JobAdmin(JobAdmin, DefaultModelAdmin):
    @admin.display(description="DKRON Link")
    def get_dkron_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank" rel="noopener" '
            'style="display:flex;justify-content:center;align-items:center;">'
            '<span class="material-symbols-outlined" '
            'style="vertical-align:middle;">link</span>'
            "</a>",
            utils.job_executions(obj.name),
        )


# Administration dbcleanup TableAdmin  and Filters Patch
admin.site.unregister(Table)


class TableAppFilter(DropdownFilter):
    title = "App"
    parameter_name = "app_label"

    def lookups(self, request, model_admin):
        unique_labels = {x._meta.app_label for x in dbcleanup_utils.model_tables().values()}
        return [(x, x) for x in unique_labels]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return None
        app_tables = [k for k, v in dbcleanup_utils.model_tables().items() if v._meta.app_label == val]
        return queryset.filter(name__in=app_tables)


class TableModelFilter(DropdownFilter):
    title = "Model"
    parameter_name = "label"

    def lookups(self, request, model_admin):
        unique_labels = {x._meta.label for x in dbcleanup_utils.model_tables().values()}
        return [(x, x) for x in unique_labels]

    def queryset(self, request, queryset):
        val = self.value()
        if val is None:
            return None
        app_tables = [k for k, v in dbcleanup_utils.model_tables().items() if v._meta.label == val]
        return queryset.filter(name__in=app_tables)


@admin.register(Table)
class TableAdmin(TableAdmin, DefaultModelAdmin):
    list_filter = (
        TableAppFilter,
        TableModelFilter,
    )
