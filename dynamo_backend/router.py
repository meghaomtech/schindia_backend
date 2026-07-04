"""
Database router that determines whether to use Django ORM (local SQLite)
or DynamoDB (production).

Usage in views:
    from dynamo_backend.router import use_dynamo, get_db_service

    if use_dynamo():
        # Use DynamoDB service
        from dynamo_backend.services import centres_db
        centres = centres_db.list_centres()
    else:
        # Use Django ORM
        centres = Centre.objects.all()
"""

from decouple import config

DJANGO_ENV = config('DJANGO_ENV', default='local')


def use_dynamo():
    """Returns True if the app should use DynamoDB (production/dev on AWS)."""
    return DJANGO_ENV in ('production', 'dev')


def is_local():
    """Returns True if running locally with SQLite."""
    return DJANGO_ENV == 'local'
