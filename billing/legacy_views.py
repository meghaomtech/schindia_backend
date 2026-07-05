"""
Legacy endpoints for the invoice generator feature.
These match the old Lambda API paths: /centers, /invoices, /invoices/:id
"""

import re
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo


# Field name conversion utilities
def _to_camel(snake_str):
    """Convert snake_case to camelCase."""
    parts = snake_str.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])


def _to_snake(camel_str):
    """Convert camelCase to snake_case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()


def _convert_keys(data, converter):
    """Convert all dict keys using the given converter function."""
    if isinstance(data, dict):
        return {converter(k): _convert_keys(v, converter) for k, v in data.items()}
    if isinstance(data, list):
        return [_convert_keys(item, converter) for item in data]
    return data


# In-memory/DynamoDB store for invoice-generator centers
# (These are separate from the main Centre model — used only by the invoice generator)

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centers_view(request):
    """List or create invoice-generator centers."""
    if use_dynamo():
        from dynamo_backend.services import centres_db

        if request.method == 'GET':
            centres = centres_db.list_centres()
            # Convert snake_case DB fields to camelCase for frontend
            centres_camel = [_convert_keys(c, _to_camel) for c in centres]
            return Response({'centers': centres_camel})
        else:
            # Convert camelCase from frontend to snake_case for DB storage
            data = _convert_keys(request.data, _to_snake)
            # Remove non-updatable fields
            data.pop('id', None)
            data.pop('rooms', None)
            center_code = data.get('center_code', '')
            if center_code:
                all_centres = centres_db.list_centres()
                existing = next((c for c in all_centres if c.get('center_code') == center_code), None)
                if existing:
                    centres_db.update_centre(existing['id'], data)
                    updated = centres_db.get_centre(existing['id'])
                    return Response(_convert_keys(updated, _to_camel), status=status.HTTP_200_OK)
            centre = centres_db.create_centre(data)
            return Response(_convert_keys(centre, _to_camel), status=status.HTTP_201_CREATED)
    else:
        from centres.models import Centre
        if request.method == 'GET':
            centres = list(Centre.objects.values())
            return Response({'centers': centres})
        else:
            return Response({'detail': 'Use /api/v1/centres/ for local mode.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def center_delete_view(request, center_code):
    """Delete a center by code."""
    if use_dynamo():
        from dynamo_backend.services import centres_db
        all_centres = centres_db.list_centres()
        centre = next((c for c in all_centres if c.get('system_id') == center_code or c.get('center_code') == center_code), None)
        if centre:
            centres_db.delete_centre(centre['id'])
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoices_view(request):
    """List or create invoices (legacy format for invoice generator)."""
    if use_dynamo():
        from dynamo_backend.services import billing_db

        user_id = str(request.user.id)
        is_root = getattr(request.user, 'role', '') == 'root'

        if request.method == 'GET':
            if is_root:
                invoices = billing_db.list_invoices()
            else:
                invoices = billing_db.list_invoices(user_id=user_id)
            # Convert snake_case to camelCase for frontend
            invoices_camel = [_convert_keys(inv, _to_camel) for inv in invoices]
            return Response({'invoices': invoices_camel})
        else:
            # Convert camelCase from frontend to snake_case for DB
            data = _convert_keys(request.data, _to_snake)
            if hasattr(data, 'copy'):
                data = data.copy()
            else:
                data = dict(data)
            data['user_id'] = user_id
            if isinstance(data, dict):
                invoice = billing_db.create_invoice(data)
                return Response(_convert_keys(invoice, _to_camel), status=status.HTTP_201_CREATED)
            return Response({'detail': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'invoices': []})


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_detail_view(request, invoice_id):
    """Get or delete a single invoice by ID or invoice number."""
    if use_dynamo():
        from dynamo_backend.services import billing_db

        # Try lookup by ID first, then by invoice_number field
        invoice = billing_db.get_invoice(invoice_id)
        if not invoice:
            # Fallback: search by invoice_number field
            all_invoices = billing_db.invoices.query_by_field('invoice_number', invoice_id)
            invoice = all_invoices[0] if all_invoices else None
            if invoice:
                invoice['items'] = billing_db.list_invoice_items(invoice['id'])

        if not invoice:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        is_root = getattr(request.user, 'role', '') == 'root'
        if not is_root and invoice.get('user_id') != str(request.user.id):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'DELETE':
            billing_db.delete_invoice(invoice['id'])
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(_convert_keys(invoice, _to_camel))
    return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
