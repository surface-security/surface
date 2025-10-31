from django.urls import reverse_lazy


def check_permission(permission):
    """
    Callback function to check if the user has a specific permission.
    This is used in the sidebar menu to conditionally display items based on permissions.
    """

    def checker(request):
        if user := getattr(request, "user", None):
            return user.has_perm(permission)
        return False

    return checker


SIDEBAR = {
    "show_search": True,
    "show_all_applications": True,
    "navigation": [
        {
            "title": "Navigation",
            "items": [
                {
                    "title": "Dashboard",
                    "icon": "dashboard",
                    "link": reverse_lazy("admin:index"),
                },
            ],
        },
        {
            "title": "Administration",
            "icon": "admin_panel_settings",
            "collapsible": True,
            "items": [
                {
                    "title": "Notifications Logs",
                    "icon": "notifications",
                    "link": reverse_lazy("admin:notifications_notification_changelist"),
                    "permission": check_permission("notifications.view_notification"),
                },
                {
                    "title": "Notifications Events",
                    "icon": "event",
                    "link": reverse_lazy("admin:notifications_event_changelist"),
                    "permission": check_permission("notifications.view_event"),
                },
                {
                    "title": "Notifications Subscriptions",
                    "icon": "subscriptions",
                    "link": reverse_lazy("admin:notifications_subscription_changelist"),
                    "permission": check_permission("notifications.view_subscription"),
                },
                {
                    "title": "Database Logs (Migrations)",
                    "icon": "storage",
                    "link": reverse_lazy("admin:migrations_migration_changelist"),
                    "permission": check_permission("admin.view_logentry"),
                },
                {
                    "title": "Database Info (Size)",
                    "icon": "table_chart",
                    "link": "/dbcleanup/table/",
                    "permission": check_permission("auth.view_user"),
                },
                {
                    "title": "Cron Jobs (dkron)",
                    "icon": "schedule",
                    "link": reverse_lazy("admin:dkron_job_changelist"),
                    "permission": check_permission("dkron.view_job"),
                },
                {
                    "title": "REST API Tokens",
                    "icon": "vpn_key",
                    "link": reverse_lazy("admin:apitokens_token_changelist"),
                    "permission": check_permission("apitokens.view_token"),
                },
                {
                    "title": "Users permission (Surface)",
                    "icon": "person",
                    "link": reverse_lazy("admin:auth_user_changelist"),
                    "permission": check_permission("auth.view_user"),
                },
                {
                    "title": "Groups permission (Surface)",
                    "icon": "group",
                    "link": reverse_lazy("admin:auth_group_changelist"),
                    "permission": check_permission("auth.view_group"),
                },
            ],
        },
        {
            "title": "CMDB",
            "icon": "map",
            "collapsible": True,
            "items": [
                {
                    "title": "Applications (TLAs) (All)",
                    "icon": "apps",
                    "link": reverse_lazy("admin:inventory_application_changelist"),
                    "permission": check_permission("inventory.view_application"),
                },
                {
                    "title": "Git (Repos) Sources",
                    "icon": "code",
                    "link": reverse_lazy("admin:inventory_gitsource_changelist"),
                    "permission": check_permission("inventory.view_gitsource"),
                },
            ],
        },
        {
            "title": "DNS & IPs",
            "icon": "dns",
            "collapsible": True,
            "items": [
                {
                    "title": "Sources",
                    "icon": "source",
                    "link": reverse_lazy("admin:dns_ips_source_changelist"),
                    "permission": check_permission("dns_ips.view_source"),
                },
                {
                    "title": "Tags",
                    "icon": "label",
                    "link": reverse_lazy("admin:dns_ips_tag_changelist"),
                    "permission": check_permission("dns_ips.view_tag"),
                },
                {
                    "title": "IP Addresses",
                    "icon": "pin_drop",
                    "link": reverse_lazy("admin:dns_ips_ipaddress_changelist"),
                    "permission": check_permission("dns_ips.view_ipaddress"),
                },
                {
                    "title": "IP Ranges",
                    "icon": "swap_horiz",
                    "link": reverse_lazy("admin:dns_ips_iprange_changelist"),
                    "permission": check_permission("dns_ips.view_iprange"),
                },
                {
                    "title": "DNS Domains",
                    "icon": "domain",
                    "link": reverse_lazy("admin:dns_ips_dnsdomain_changelist"),
                    "permission": check_permission("dns_ips.view_dnsdomain"),
                },
                {
                    "title": "DNS Records",
                    "icon": "dns",
                    "link": reverse_lazy("admin:dns_ips_dnsrecord_changelist"),
                    "permission": check_permission("dns_ips.view_dnsrecord"),
                },
                {
                    "title": "DNS Record Values",
                    "icon": "fact_check",
                    "link": reverse_lazy("admin:dns_ips_dnsrecordvalue_changelist"),
                    "permission": check_permission("dns_ips.view_dnsrecordvalue"),
                },
            ],
        },
        {
            "title": "Security Testing & VM",
            "icon": "search",
            "collapsible": True,
            "items": [
                {
                    "title": "Findings (All)",
                    "icon": "find_in_page",
                    "link": reverse_lazy("admin:vulns_finding_changelist"),
                    "permission": check_permission("vulns.view_finding"),
                },
            ],
        },
        {
            "title": "Secure SDLC / AppSec",
            "icon": "security",
            "collapsible": True,
            "items": [
                {
                    "title": "SCA - Dependencies",
                    "icon": "extension",
                    "link": reverse_lazy("admin:sca_scadependency_changelist"),
                    "permission": check_permission("sca.view_scadependency"),
                },
                {
                    "title": "SCA - Projects",
                    "icon": "workspaces",
                    "link": reverse_lazy("admin:sca_scaproject_changelist"),
                    "permission": check_permission("sca.view_scaproject"),
                },
                {
                    "title": "SCA - Dependencies (EoL)",
                    "icon": "event_busy",
                    "link": reverse_lazy("admin:sca_endoflifedependency_changelist"),
                    "permission": check_permission("sca.view_endoflifedependency"),
                },
                {
                    "title": "SCA - Findings (Suppressed)",
                    "icon": "block",
                    "link": reverse_lazy("admin:sca_suppressedscafinding_changelist"),
                    "permission": check_permission("sca.view_suppressedscafinding"),
                },
            ],
        },
        {
            "title": "Rootboxes & Scanners",
            "icon": "host",
            "collapsible": True,
            "items": [
                {
                    "title": "Scanners Logs",
                    "icon": "list_alt",
                    "link": reverse_lazy("admin:scanners_scanlog_changelist"),
                    "permission": check_permission("scanners.view_scanlog"),
                },
                {
                    "title": "Rootboxes",
                    "icon": "dns",
                    "link": reverse_lazy("admin:scanners_rootbox_changelist"),
                    "permission": check_permission("scanners.view_rootbox"),
                },
                {
                    "title": "Scanners",
                    "icon": "search",
                    "link": reverse_lazy("admin:scanners_scanner_changelist"),
                    "permission": check_permission("scanners.view_scanner"),
                },
                {
                    "title": "Scanners Images",
                    "icon": "image",
                    "link": reverse_lazy("admin:scanners_scannerimage_changelist"),
                    "permission": check_permission("scanners.view_scannerimage"),
                },
                {
                    "title": "Live Webservers",
                    "icon": "public",
                    "link": reverse_lazy("admin:scanners_livehost_changelist"),
                    "permission": check_permission("scanners.view_livehost"),
                },
                {
                    "title": "Raw Results",
                    "icon": "description",
                    "link": reverse_lazy("admin:scanners_rawresult_changelist"),
                    "permission": check_permission("scanners.view_rawresult"),
                },
            ],
        },
    ],
}
