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
    ],
}
