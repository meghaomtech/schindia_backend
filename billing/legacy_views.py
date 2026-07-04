"""
Legacy endpoints for the invoice generator feature.
These match the old Lambda API paths: /centers, /invoices, /invoices/:id
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo


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
            return Response({'centers': centres})
        else:
            data = request.data
            center_code = data.get('centerCode', '')
            if center_code:
                all_centres = centres_db.list_centres()
                existing = next((c for c in all_centres if c.get('centerCode') == center_code), None)
                if existing:
                    centres_db.update_centre(existing['id'], data)
                    updated = centres_db.get_centre(existing['id'])
                    return Response(updated, status=status.HTTP_200_OK)
            centre = centres_db.create_centre(data)
            return Response(centre, status=status.HTTP_201_CREATED)
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
        centre = next((c for c in all_centres if c.get('system_id') == center_code or c.get('centerCode') == center_code), None)
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
            return Response({'invoices': invoices})
        else:
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            data['user_id'] = user_id
            if isinstance(data, dict):
                invoice = billing_db.create_invoice(data)
                return Response(invoice, status=status.HTTP_201_CREATED)
            return Response({'detail': 'Invalid data.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({'invoices': []})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_detail_view(request, invoice_id):
    """Get a single invoice by ID or number."""
    if use_dynamo():
        from dynamo_backend.services import billing_db
        invoice = billing_db.get_invoice(invoice_id)
        if not invoice:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        is_root = getattr(request.user, 'role', '') == 'root'
        if not is_root and invoice.get('user_id') != str(request.user.id):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(invoice)
    return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
