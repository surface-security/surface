import logging
from urllib.parse import quote

from django.apps import apps
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from jsoneditor.forms import JSONEditor
from unfold.admin import ModelAdmin

from django_restful_admin import site as rest

logger = logging.getLogger(__name__)

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


class ReverseReadonlyMixin:
    """
    Mixin to add a readonly 'reverse' field showing related objects in Django admin.
    Should be used with ModelAdmin or a compatible base class.
    """

    def get_readonly_fields(self, request, obj=None):
        parent_method = getattr(super(), "get_readonly_fields", None)
        fields = list(parent_method(request, obj)) if parent_method else []
        if obj and "reverse" not in fields:
            fields.append("reverse")
        return fields

    def get_fieldsets(self, request, obj=None):
        parent_method = getattr(super(), "get_fieldsets", None)
        fieldsets = list(parent_method(request, obj)) if parent_method else []
        if not fieldsets:
            return fieldsets
        label, opts = fieldsets[0]
        opts = dict(opts)
        opts.setdefault("classes", []).append("tab")
        if "fields" in opts:
            opts["fields"] = tuple(f for f in opts["fields"] if f != "reverse")
        fieldsets[0] = ("General", opts)
        if obj:
            fieldsets.append(("Relationships", {"classes": ["tab"], "fields": ("reverse",)}))
        return tuple(fieldsets)

    def reverse(self, obj):
        """Render all relationships for the current object."""
        if not obj or not obj.pk:
            return format_html("<div>No relationships available for new objects.</div>")
        try:
            html = self._render_relationships(obj)
            return format_html("<div class='relationships-container'>{}</div>", html)
        except Exception as e:
            return format_html("<div class='text-red-500'>Error loading relationships: {}</div>", str(e))

    def _render_relationships(self, obj):
        html = []
        forward_html = self._get_forward_relationships(obj)
        if forward_html:
            html.append("<strong>Forward Relationships</strong>")
            html.append(forward_html)
        reverse_html = self._get_reverse_relationships(obj)
        if reverse_html:
            html.append("<br><strong>Reverse Relationships</strong>")
            html.append(reverse_html)
        if not html:
            html.append("<div>No relationships found.</div>")
        return mark_safe("\n".join(html))

    def _get_forward_relationships(self, obj):
        html = []
        opts = obj._meta
        for field in opts.get_fields():
            if field.is_relation:
                try:
                    if not field.many_to_many and hasattr(field, "related_model"):
                        rel_obj = getattr(obj, field.name, None)
                        if rel_obj:
                            html.append(
                                self._format_relation(field, rel_obj, single_obj=True, relation_type="ForeignKey")
                            )
                    elif field.many_to_many and not field.auto_created:
                        manager = getattr(obj, field.name)
                        rel_objs = manager.all()[:10]
                        total_count = manager.count()
                        if rel_objs:
                            html.append(self._format_relation(field, rel_objs, total_count, "ManyToMany"))
                except AttributeError:
                    continue
        return mark_safe("\n".join(html))

    def _get_reverse_relationships(self, obj):
        html = []
        opts = obj._meta
        for field in opts.get_fields():
            if field.auto_created and field.is_relation:
                try:
                    manager = getattr(obj, field.get_accessor_name())
                    if field.one_to_many:
                        rel_objs = manager.all()[:10]
                        total_count = manager.count()
                        if rel_objs:
                            html.append(self._format_relation(field, rel_objs, total_count, "ForeignKey"))
                    elif field.one_to_one:
                        rel_obj = getattr(manager, getattr(field.related_model._meta, "model_name", ""), None)
                        if rel_obj:
                            html.append(
                                self._format_relation(field, rel_obj, single_obj=True, relation_type="OneToOne")
                            )
                    elif field.many_to_many:
                        rel_objs = manager.all()[:10]
                        total_count = manager.count()
                        if rel_objs:
                            html.append(self._format_relation(field, rel_objs, total_count, "ManyToMany"))
                except AttributeError:
                    continue
        return mark_safe("\n".join(html))

    def _format_relation(self, field, related_objs, total_count=None, relation_type=None, single_obj=False):
        label = getattr(field, "verbose_name", None)
        if not label and hasattr(field, "related_model") and field.related_model:
            label = getattr(field.related_model._meta, "verbose_name_plural", str(field.related_model))
        label = label.title() if isinstance(label, str) else str(field)
        rel_type = relation_type or "Relation"
        header = f'<div class="py-1">{label}: <b>{rel_type}</b>'
        if total_count is not None:
            header += f" ({total_count} total)"
        header += "</div>"

        def obj_link(obj):
            url = self._get_admin_url(obj)
            return f'<a href="{url}" style="color: rgb(59, 130, 246);">{obj}</a>' if url else str(obj)

        if single_obj:
            body = f'<div class="pl-4" style="padding-left:2em">• {obj_link(related_objs)}</div>'
        else:
            body = "\n".join(
                f'<div class="pl-4" style="padding-left:2em">• {obj_link(obj)}</div>' for obj in related_objs
            )
            if total_count and total_count > 10:
                body += (
                    f'\n<div class="pl-4 text-gray-500" style="padding-left:2em">... and {total_count - 10} more</div>'
                )
        return mark_safe(header + "\n" + body)

    def _get_admin_url(self, obj):
        if not obj or not obj.pk:
            return None
        try:
            opts = obj._meta
            return reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[quote(str(obj.pk))])
        except Exception:
            return None
