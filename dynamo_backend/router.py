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
    """Returns True — always use DynamoDB regardless of environment."""
    return True


def is_local():
    """Returns True if running locally."""
    return DJANGO_ENV == 'local'
