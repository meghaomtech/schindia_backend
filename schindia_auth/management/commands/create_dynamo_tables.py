"""
Management command to create all DynamoDB tables.
Usage: python manage.py create_dynamo_tables
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create all DynamoDB tables for the Shichida backend'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete all tables instead of creating them',
        )

    def handle(self, *args, **options):
        from dynamo_backend.setup_tables import create_all_tables, delete_all_tables

        if options['delete']:
            self.stdout.write(self.style.WARNING('Deleting all DynamoDB tables...'))
            delete_all_tables()
            self.stdout.write(self.style.SUCCESS('Done.'))
        else:
            self.stdout.write('Creating DynamoDB tables...')
            create_all_tables()
            self.stdout.write(self.style.SUCCESS('Done.'))
