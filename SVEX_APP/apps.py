from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone


class SvexAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "SVEX_APP"

    def ready(self):
        from . import signals


@receiver(user_logged_in)
def update_last_login(sender, user, **kwargs):
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
