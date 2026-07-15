"""
Database router for DynamoDB.

All environments (including local development) use DynamoDB.
The Django ORM paths exist only as fallback scaffolding and are not
exercised in normal operation.

Usage in views:
    from dynamo_backend.router import use_dynamo

    if use_dynamo():
        from dynamo_backend.services import centres_db
        centres = centres_db.list_centres()
"""

from decouple import config

DJANGO_ENV = config('DJANGO_ENV', default='local')


def use_dynamo():
    """Always True — DynamoDB is the primary datastore for all environments."""
    return True


def is_local():
    """Returns True if DJANGO_ENV is 'local'. Used for environment-specific config (e.g. logging)."""
    return DJANGO_ENV == 'local'
