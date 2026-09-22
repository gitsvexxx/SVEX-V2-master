from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Client

User = get_user_model()

CLIENT_GROUP_NAME = "Clients"
ADMIN_GROUP_NAME = "Admins"
MANAGER_GROUP_NAME = "Managers"


@receiver(post_save, sender=User, dispatch_uid="create_client_for_user")
def create_client_for_user(sender, instance, created, **kwargs):
    if created:
        Client.objects.get_or_create(user=instance)


@receiver(post_save, sender=User, dispatch_uid="assign_user_to_group")
def assign_user_to_group(sender, instance, created, **kwargs):
    if created:
        group_name = CLIENT_GROUP_NAME

        if instance.is_superuser:
            group_name = ADMIN_GROUP_NAME
        elif instance.is_manager:
            group_name = MANAGER_GROUP_NAME

        group, _ = Group.objects.get_or_create(name=group_name)
        instance.groups.add(group)
