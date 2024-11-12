from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Secret, SecretHistory, SecretLocation

@admin.register(Secret)
class SecretAdmin(admin.ModelAdmin):
    list_display = (
        'secret_preview',
        'kind',
        'source',
        'git_source_link',
        'location_links',
        'status',
        'criticality',
        'locations_detail',
        'verified',
        'updated_at'
    )
    list_editable = ('status', 'criticality')
    list_filter = ('source', 'status', 'criticality', 'verified', 'team', 'git_source', 'secret_hash')
    search_fields = ('secret', 'source', 'kind', 'team', 'git_source__repo_url', 'secret_hash')
    readonly_fields = ('created_at', 'updated_at', 'updated_by', 'version', 'secret_hash')
    
    def secret_preview(self, obj):
        return obj.secret[:30] + '...' if len(obj.secret) > 30 else obj.secret
    secret_preview.short_description = 'Secret'
    
    def git_source_link(self, obj):
        if obj.git_source:
            return format_html('<a href="{}" target="_blank">{}</a>', 
                obj.git_source.repo_url, 
                obj.git_source.repo_url)
        return ''
    git_source_link.short_description = 'Repository'
    
    def location_links(self, obj):
        """Numbered links to specific files in repository"""
        locations = obj.locations.all()
        if locations:
            links = []
            max_links = 10
            total_links = locations.count()

            for idx, loc in enumerate(locations[:max_links], 1):
                # Clean up repository URL
                repo = loc.repository.replace('.git', '')
                if 'truffleho/' in repo:
                    repo = repo.replace('truffleho/', 'trufflehog/')

                url = f"{repo}/blob/{loc.commit}/{loc.file_path}#L{loc.line}"
                links.append(
                    format_html(
                        '<a href="{}" target="_blank" title="Line {}">{}</a>',
                        url,
                        loc.line,
                        str(idx)
                    )
                )

            if total_links > max_links:
                links.append(
                    format_html(
                        '<span title="{} more locations">...</span>',
                        total_links - max_links
                    )
                )
            
            return format_html(', '.join(links))
        return ''
    location_links.short_description = 'Sources'

    def locations_detail(self, obj):
        """Magnifying glass icon for detailed locations view"""
        locations_count = obj.locations.count()
        if locations_count > 0:
            url = reverse('admin:secretsmanager_secretlocation_changelist') + f'?secret__id={obj.id}'
            return format_html(
                '<a href="{}" title="{} locations" style="text-decoration:none;">🔍 {}</a>',
                url,
                locations_count,
                locations_count
            )
        return ''
    locations_detail.short_description = 'Locations'

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

@admin.register(SecretLocation)
class SecretLocationAdmin(admin.ModelAdmin):
    list_display = ('secret_preview', 'file_path', 'commit_link', 'timestamp', 'author')
    list_filter = ('secret', 'repository', 'author')
    search_fields = ('file_path', 'commit', 'author', 'secret__secret')

    def secret_preview(self, obj):
        """Show the actual secret value instead of the model string representation"""
        secret_value = obj.secret.secret
        return secret_value[:30] + '...' if len(secret_value) > 30 else secret_value
    secret_preview.short_description = 'Secret'

    def commit_link(self, obj):
        url = f"{obj.repository}/commit/{obj.commit}"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.commit[:8])
    commit_link.short_description = 'Commit'