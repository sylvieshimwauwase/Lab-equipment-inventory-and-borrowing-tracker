from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

MODELS = ['category', 'item', 'borrower', 'borrowrecord']
APPS = ['Inventory', 'Borrowing']

ROLES = {
    'Staff': ['view', 'add', 'change'],                    # no delete
    'Manager': ['view', 'add', 'change', 'delete'],        # everything
}


class Command(BaseCommand):
    help = "Create the Staff and Manager groups with their permissions."

    def handle(self, *args, **options):
        for role, actions in ROLES.items():
            codenames = [f'{a}_{m}' for m in MODELS for a in actions]
            perms = Permission.objects.filter(
                codename__in=codenames, content_type__app_label__in=APPS)
            group, _ = Group.objects.get_or_create(name=role)
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(
                f'{role}: {perms.count()} permissions assigned.'))