from django.apps import apps
from django.db import models
from jsoneditor.forms import JSONEditor
from unfold.admin import ModelAdmin

from django_restful_admin import site as rest

# Register all models for REST API except the registered ones
for model in apps.get_models():
    if model in rest._registry:
        continue
    rest.register(model)


class DefaultModelAdmin(ModelAdmin):
    list_filter_submit = True
    list_filter_sheet = False
    list_fullwidth = True
    add_fieldsets = ()
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditor(attrs={"style": "background-color: white !important;"})}
    }

    def get_list_display(self, request):
        """
        make sure model primary key is always present as first column for standard UX
        """
        default_list_display = list(super(DefaultModelAdmin, self).get_list_display(request))

        pk = self.model._meta.pk.name
        if pk in default_list_display:
            default_list_display.remove(pk)
        default_list_display.insert(0, self.model._meta.pk.name)

        return default_list_display

    def get_list_display_links(self, request, list_display):
        default_list_display_links = super(DefaultModelAdmin, self).get_list_display_links(request, list_display)

        if not default_list_display_links:
            default_list_display_links = ("pk",)

        return default_list_display_links
