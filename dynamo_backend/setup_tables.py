"""
Create all DynamoDB tables for the Shichida backend.
Run this once per environment to provision tables.

Usage:
    python manage.py shell -c "from dynamo_backend.setup_tables import create_all_tables; create_all_tables()"

Or:
    python manage.py create_dynamo_tables
"""

from .client import get_dynamodb_resource
from .tables import (
    USERS_TABLE, CENTRES_TABLE, ROOMS_TABLE, SESSIONS_TABLE,
    SESSION_SLOTS_TABLE, CHILDREN_TABLE, CONTACTS_TABLE,
    ENROLMENTS_TABLE, JOURNEY_TABLE, NOTES_TABLE,
    INVOICES_TABLE, INVOICE_ITEMS_TABLE, PURCHASES_TABLE,
    ROLES_TABLE, ROLE_PERMISSIONS_TABLE, ROLE_MEMBERS_TABLE,
    ATTENDANCE_TABLE, COURSE_PROGRESS_TABLE,
    OTP_TOKENS_TABLE, ROOT_ACCESS_REQUESTS_TABLE, JWT_BLACKLIST_TABLE,
)


TABLE_DEFINITIONS = [
    {
        'TableName': USERS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'email-index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': CENTRES_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'system_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'system_id-index',
                'KeySchema': [{'AttributeName': 'system_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': ROOMS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'centre_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'centre_id-index',
                'KeySchema': [{'AttributeName': 'centre_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': SESSIONS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'centre_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'centre_id-index',
                'KeySchema': [{'AttributeName': 'centre_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': SESSION_SLOTS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'centre_id', 'AttributeType': 'S'},
            {'AttributeName': 'room_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'centre_id-index',
                'KeySchema': [{'AttributeName': 'centre_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'room_id-index',
                'KeySchema': [{'AttributeName': 'room_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
    },
    {
        'TableName': CHILDREN_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'centre_id', 'AttributeType': 'S'},
            {'AttributeName': 'system_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'centre_id-index',
                'KeySchema': [{'AttributeName': 'centre_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'system_id-index',
                'KeySchema': [{'AttributeName': 'system_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
    },
    {
        'TableName': CONTACTS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'child_id-index',
                'KeySchema': [{'AttributeName': 'child_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': ENROLMENTS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'child_id-index',
                'KeySchema': [{'AttributeName': 'child_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': JOURNEY_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'child_id-index',
                'KeySchema': [{'AttributeName': 'child_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': NOTES_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'child_id-index',
                'KeySchema': [{'AttributeName': 'child_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': INVOICES_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'child_id-index',
                'KeySchema': [{'AttributeName': 'child_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'user_id-index',
                'KeySchema': [{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
    },
    {
        'TableName': INVOICE_ITEMS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'invoice_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'invoice_id-index',
                'KeySchema': [{'AttributeName': 'invoice_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': PURCHASES_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'child_id-index',
                'KeySchema': [{'AttributeName': 'child_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': ROLES_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'centre_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'centre_id-index',
                'KeySchema': [{'AttributeName': 'centre_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': ROLE_PERMISSIONS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'role_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'role_id-index',
                'KeySchema': [{'AttributeName': 'role_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': ROLE_MEMBERS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'role_id', 'AttributeType': 'S'},
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'role_id-index',
                'KeySchema': [{'AttributeName': 'role_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'user_id-index',
                'KeySchema': [{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
    },
    # New Phase 2 tables
    {
        'TableName': ATTENDANCE_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
            {'AttributeName': 'date', 'AttributeType': 'S'},
            {'AttributeName': 'slot_id', 'AttributeType': 'S'},
            {'AttributeName': 'session_id', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'child_id-index',
                'KeySchema': [
                    {'AttributeName': 'child_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'date', 'KeyType': 'RANGE'},
                ],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'slot_id-index',
                'KeySchema': [{'AttributeName': 'slot_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
            {
                'IndexName': 'session_id-index',
                'KeySchema': [{'AttributeName': 'session_id', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            },
        ],
    },
    {
        'TableName': COURSE_PROGRESS_TABLE,
        'KeySchema': [{'AttributeName': 'child_id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'child_id', 'AttributeType': 'S'},
        ],
        # No GSI needed — 1:1 relationship, direct get/put by child_id
    },
    # Phase: SQLite removal — auth tables
    {
        'TableName': OTP_TOKENS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'email-index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': ROOT_ACCESS_REQUESTS_TABLE,
        'KeySchema': [{'AttributeName': 'id', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'email', 'AttributeType': 'S'},
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'email-index',
                'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                'Projection': {'ProjectionType': 'ALL'},
            }
        ],
    },
    {
        'TableName': JWT_BLACKLIST_TABLE,
        'KeySchema': [{'AttributeName': 'jti', 'KeyType': 'HASH'}],
        'AttributeDefinitions': [
            {'AttributeName': 'jti', 'AttributeType': 'S'},
        ],
        # TTL attribute 'expires_at' enabled separately below via update_time_to_live
    },
]


def enable_ttl():
    """Enable DynamoDB TTL on the JWT blacklist table so expired entries self-purge."""
    client = get_dynamodb_resource().meta.client
    client.update_time_to_live(
        TableName=JWT_BLACKLIST_TABLE,
        TimeToLiveSpecification={'Enabled': True, 'AttributeName': 'expires_at'},
    )


def create_all_tables():
    """Create all DynamoDB tables. Skips existing ones."""
    dynamodb = get_dynamodb_resource()

    existing_tables = [t.name for t in dynamodb.tables.all()]

    for table_def in TABLE_DEFINITIONS:
        table_name = table_def['TableName']

        if table_name in existing_tables:
            print(f"  ✓ {table_name} (already exists)")
            continue

        params = {
            'TableName': table_name,
            'KeySchema': table_def['KeySchema'],
            'AttributeDefinitions': table_def['AttributeDefinitions'],
            'BillingMode': 'PAY_PER_REQUEST',  # On-demand pricing
        }

        if 'GlobalSecondaryIndexes' in table_def:
            gsi_list = []
            for gsi in table_def['GlobalSecondaryIndexes']:
                gsi_list.append({
                    'IndexName': gsi['IndexName'],
                    'KeySchema': gsi['KeySchema'],
                    'Projection': gsi['Projection'],
                })
            params['GlobalSecondaryIndexes'] = gsi_list

        dynamodb.create_table(**params)
        print(f"  ✓ {table_name} (created)")

        if table_name == JWT_BLACKLIST_TABLE:
            dynamodb.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            enable_ttl()
            print(f"    ↳ TTL enabled on {table_name}")

    print("\nAll tables provisioned successfully!")


def delete_all_tables():
    """Delete all DynamoDB tables. USE WITH CAUTION."""
    dynamodb = get_dynamodb_resource()

    for table_def in TABLE_DEFINITIONS:
        table_name = table_def['TableName']
        try:
            table = dynamodb.Table(table_name)
            table.delete()
            print(f"  ✗ {table_name} (deleted)")
        except Exception as e:
            print(f"  - {table_name} (skip: {e})")
