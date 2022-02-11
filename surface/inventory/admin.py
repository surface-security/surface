from django.contrib import admin
from django.contrib.admin.decorators import register
from . import models


@register(models.Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    empty for now
    """
