"""
Seed the three built-in global roles (Super Admin, Centre Manager, Affiliate)
so Global Roles & Permissions has something to show on first run.

Usage: python manage.py seed_global_access
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed built-in global roles (Super Admin, Centre Manager, Affiliate) into DynamoDB'

    def handle(self, *args, **options):
        from dynamo_backend.services import global_access_db
        from global_access.permissions_catalog import SEED_ROLES

        existing = {r.get('kind'): r for r in global_access_db.list_roles() if r.get('kind')}

        for seed in SEED_ROLES:
            kind = seed['kind']
            if kind in existing:
                self.stdout.write(f"  ✓ {seed['name']} (already exists)")
                continue

            grants = seed['grants']
            permissions = [{'key': key, 'edit': level == 'edit', 'visible': True} for key, level in grants.items()]

            role = global_access_db.create_role({
                'kind': kind,
                'name': seed['name'],
                'description': seed['description'],
                'permissions': permissions,
            })
            self.stdout.write(self.style.SUCCESS(f"  ✓ {role['name']} (created)"))

        self.stdout.write(self.style.SUCCESS('Done.'))
