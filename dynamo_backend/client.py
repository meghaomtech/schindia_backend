"""
DynamoDB client singleton.
Provides a configured boto3 DynamoDB resource for production use.
"""

import boto3
from decouple import config

_dynamodb_resource = None
_dynamodb_client = None


def get_dynamodb_resource():
    """Get a boto3 DynamoDB resource (high-level API)."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource(
            'dynamodb',
            aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
            region_name=config('AWS_REGION', default='ap-south-1'),
        )
    return _dynamodb_resource


def get_dynamodb_client():
    """Get a boto3 DynamoDB client (low-level API)."""
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = boto3.client(
            'dynamodb',
            aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
            region_name=config('AWS_REGION', default='ap-south-1'),
        )
    return _dynamodb_client


def get_table(table_name):
    """Get a DynamoDB Table resource by name."""
    resource = get_dynamodb_resource()
    return resource.Table(table_name)
