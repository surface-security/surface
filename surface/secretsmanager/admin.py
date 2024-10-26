from django.contrib import admin
from .models import Secret, SecretHistory

@admin.register(Secret)
class SecretAdmin(admin.ModelAdmin):
    list_display = ('kind', 'source', 'status', 'criticality', 'verified', 'updated_at')
    list_filter = ('status', 'criticality', 'verified', 'team')
    search_fields = ('secret', 'source', 'kind', 'team')
    readonly_fields = ('created_at', 'updated_at', 'updated_by', 'version')

    def save_model(self, request, obj, form, change):
        if change:
            obj.version += 1
            SecretHistory.objects.create(
                secret=obj,
                changed_fields=form.changed_data,
                changed_by=request.user,
                version=obj.version
            )
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(SecretHistory)
class SecretHistoryAdmin(admin.ModelAdmin):
    list_display = ('secret', 'version', 'changed_by', 'changed_at')
    list_filter = ('secret', 'changed_by')
    readonly_fields = ('secret', 'changed_fields', 'changed_by', 'changed_at', 'version')