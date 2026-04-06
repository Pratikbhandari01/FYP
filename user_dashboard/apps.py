from django.apps import AppConfig
from django.contrib.admin.sites import NotRegistered


class UserDashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_dashboard'

    def ready(self):
        from django.contrib import admin
        from taggit.models import Tag

        try:
            admin.site.unregister(Tag)
        except NotRegistered:
            pass
