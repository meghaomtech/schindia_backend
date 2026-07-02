"""
billing/dynamodb.py — DynamoDB service layer for billing data.

Table names and region are read from Django settings, which derive them
from DJANGO_ENV automatically:
  development → ShichidaInvoices-local  (or DynamoDB Local)
  dev         → ShichidaInvoices-dev
  production  → ShichidaInvoices-prod

Set DYNAMODB_ENDPOINT=http://localhost:8001 to use DynamoDB Local.
"""

import logging
import boto3
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


def _client_kwargs() -> dict:
    kwargs = {'region_name': settings.DYNAMODB_REGION}
    if settings.DYNAMODB_ENDPOINT:
        kwargs['endpoint_url'] = settings.DYNAMODB_ENDPOINT
    return kwargs


def get_client():
    return boto3.client('dynamodb', **_client_kwargs())


def get_resource():
    return boto3.resource('dynamodb', **_client_kwargs())


def get_invoices_table():
    return get_resource().Table(settings.DYNAMODB_INVOICES_TABLE)


# ── Convenience helpers ──────────────────────────────────────────────────────

def put_invoice(item: dict) -> dict:
    table = get_invoices_table()
    try:
        response = table.put_item(Item=item)
        logger.info("Invoice written: %s (table: %s)", item.get('invoiceId'), settings.DYNAMODB_INVOICES_TABLE)
        return response
    except ClientError as exc:
        logger.error("DynamoDB put_invoice failed: %s", exc)
        raise


def get_invoice(invoice_id: str) -> dict | None:
    table = get_invoices_table()
    try:
        response = table.get_item(Key={'invoiceId': invoice_id})
        return response.get('Item')
    except ClientError as exc:
        logger.error("DynamoDB get_invoice failed: %s", exc)
        raise


def query_invoices_by_centre(centre_code: str) -> list[dict]:
    table = get_invoices_table()
    try:
        from boto3.dynamodb.conditions import Key
        response = table.query(
            IndexName='centreCode-index',
            KeyConditionExpression=Key('centreCode').eq(centre_code),
        )
        return response.get('Items', [])
    except ClientError as exc:
        logger.error("DynamoDB query_invoices_by_centre failed: %s", exc)
        raise
