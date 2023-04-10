from django.contrib import admin
from django.contrib.admin.decorators import register
from . import models


@register(models.Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'actions')
    search_fieds = ('name', 'description', 'actions')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request):
        return False


@register(models.Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    empty for now
    """
