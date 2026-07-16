from django.core.management.base import BaseCommand
from dynamo_backend.services import auth_db


class Command(BaseCommand):
    help = 'Create the root admin user (one-time setup)'

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help='Full name of the root admin')
        parser.add_argument('--email', required=True, help='Email address')
        parser.add_argument('--password', required=True, help='Password')

    def handle(self, *args, **options):
        if auth_db.root_exists():
            self.stderr.write(self.style.ERROR('Root admin already exists.'))
            return

        name = options['name']
        parts = name.strip().split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        auth_db.create_user(
            email=options['email'],
            password=options['password'],
            first_name=first_name,
            last_name=last_name,
            role='root',
            status='approved',
        )

        self.stdout.write(self.style.SUCCESS(
            f'Root admin created: {options["email"]}'
        ))
