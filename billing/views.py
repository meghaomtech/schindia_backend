import logging
from datetime import date, datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import billing_db, centres_db, children_db
from roles.access import get_user_access, centre_not_found, permission_denied
from . import ledger
from .notifications import send_invoice_email
from .totals import compute_invoice_total, is_line_itemised
from .serializers import (
    CancelInvoiceSerializer, CorrectionSerializer, KIND_SERIALIZERS,
)

logger = logging.getLogger(__name__)


def _child_centre_id(child_id):
    """Resolve the centre a child belongs to, for scope checks."""
    if not child_id:
        return None
    child = children_db.get_child(str(child_id))
    return child.get('centre_id') if child else None


def _centre_invoice_set(centre_pk):
    """
    Every invoice belonging to a centre, however it was raised.

    Two routes reach the same centre and both are needed. Invoices stamped with
    `centre_id` are found directly — including any raised without naming a
    child, which the child walk cannot see at all. Invoices predating that
    stamp are still reachable only through their child. Older rows can satisfy
    both, so the result is deduplicated by id rather than concatenated.
    """
    by_id = {}
    for inv in billing_db.list_invoices(centre_id=str(centre_pk)):
        by_id[inv['id']] = inv
    for child in children_db.list_children(str(centre_pk)):
        for inv in billing_db.list_invoices(child_id=child['id']):
            by_id.setdefault(inv['id'], inv)
    return list(by_id.values())


def _with_balance(invoice):
    """
    Attach the derived balance so callers never compute their own.

    Two screens that each do their own arithmetic are two screens that will
    eventually disagree about what a family owes.
    """
    if not invoice:
        return invoice
    entries = billing_db.list_ledger(invoice['id'])

    # Invoices raised before the ledger existed carry a stored status and no
    # entries. Without this they would all suddenly read as fully owed, and a
    # settled invoice showing as debt is worse than useless. Treated as a
    # single synthetic payment so the figure matches what was recorded at the
    # time; anything raised from now on builds a real trail.
    if not entries and str(invoice.get('status', '')).lower() == 'paid':
        entries = [{
            'kind': ledger.PAYMENT,
            'amount': invoice.get('total_amount') or invoice.get('total') or '0',
            'reason': 'legacy: stored status was Paid',
        }]

    enriched = dict(invoice)
    enriched['balance'] = ledger.compute_balance(invoice, entries)
    return enriched


def _with_balances(invoices):
    return [_with_balance(i) for i in invoices]


class InvoiceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            access = get_user_access(request.user, request)
            if not access.can_access_centre(_child_centre_id(child_pk)):
                return centre_not_found()
            invoices = billing_db.list_invoices(child_id=str(child_pk))
        else:
            # Not centre-scoped: only ever returns the caller's own invoices.
            invoices = billing_db.list_invoices(user_id=str(request.user.id))
        return Response(_with_balances(invoices))

    def retrieve(self, request, *args, **kwargs):
        invoice = billing_db.get_invoice(str(kwargs['pk']))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_invoice_centre_id(invoice)):
            return centre_not_found('Invoice not found.')
        return Response(_with_balance(invoice))

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            access = get_user_access(request.user, request)
            if not access.can_access_centre(_child_centre_id(child_pk)):
                return centre_not_found()

        data = request.data.copy()
        data['user_id'] = str(request.user.id)

        # Stamp the centre that raised this invoice.
        #
        # Without it an invoice is only reachable by walking children, so one
        # raised at reception without naming a child — a registration fee taken
        # before enrolment — never appears in any centre's Invoice History and
        # cannot be found again afterwards.
        centre_id = (data.get('centre_id') or '').strip() or _child_centre_id(
            child_pk or data.get('child_id'))
        if centre_id:
            access = get_user_access(request.user, request)
            # A caller must not be able to file an invoice against a centre they
            # cannot see, whatever they put in the payload.
            if not access.can_access_centre(centre_id):
                return centre_not_found()
            data['centre_id'] = str(centre_id)
        else:
            # An empty string is not a legal GSI key and would fail the write.
            data.pop('centre_id', None)

        # The series advances only when we issue the number. A hand-typed
        # number is the caller's own and consumes nothing, which is what keeps
        # the series unbroken either way (INV-002).
        # The client posts `invoiceNumber`, which the camelCase parser turns
        # into `invoice_number`; stored invoices key it as `number`. Accept
        # either and normalise, or a hand-typed number is silently dropped.
        supplied = (data.get('number') or data.get('invoice_number') or '').strip()
        data['number'] = supplied or billing_db.allocate_invoice_number()
        data.pop('invoice_number', None)

        # What the invoice comes to, worked out from its own lines rather than
        # taken from the client. Without a stored total every balance resolves
        # to zero, so a freshly raised invoice reads as already settled and
        # never appears as owed, payable or overdue anywhere.
        if is_line_itemised(data):
            data['total_amount'] = str(compute_invoice_total(data))

        invoice = billing_db.create_invoice(data)

        # Say whether the invoice actually reached anyone. Saving succeeds
        # regardless — the bill exists and is owed either way — but reception
        # needs to know it did not arrive, or a parent is chased for something
        # they were never sent.
        delivery = send_invoice_email(invoice)
        payload = dict(invoice)
        payload['email_delivery'] = {
            'sent': delivery.get('sent', False),
            'reason': delivery.get('reason'),
            'recipients': [
                r['email'] for r in delivery.get('results', []) if r.get('status') == 'sent'
            ],
        }
        return Response(payload, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        invoice = billing_db.get_invoice(str(kwargs['pk']))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_invoice_centre_id(invoice)):
            return centre_not_found('Invoice not found.')
        # Recompute from the merged result, not the patch alone: a partial
        # update may change one fee and leave the rest, and a total left over
        # from the old lines is a figure the printed invoice contradicts.
        updates = request.data.copy()
        merged = {**invoice, **updates}
        if is_line_itemised(updates) and is_line_itemised(merged):
            updates['total_amount'] = str(compute_invoice_total(merged))

        invoice = billing_db.update_invoice(str(kwargs['pk']), updates)
        return Response(invoice)

    def destroy(self, request, *args, **kwargs):
        invoice = billing_db.get_invoice(str(kwargs['pk']))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_invoice_centre_id(invoice)):
            return centre_not_found('Invoice not found.')
        billing_db.delete_invoice(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Mark an invoice as sent and record the timestamp."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_invoice_centre_id(invoice)):
            return centre_not_found('Invoice not found.')
        if invoice.get('status') == 'Paid':
            return Response(
                {'detail': 'Cannot send a paid invoice.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = billing_db.update_invoice(str(pk), {
            'status': 'Sent',
            'sent_at': datetime.utcnow().isoformat(),
        })
        return Response(updated)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark an invoice as paid."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_invoice_centre_id(invoice)):
            return centre_not_found('Invoice not found.')
        updated = billing_db.update_invoice(str(pk), {'status': 'Paid'})
        return Response(updated)

    @action(detail=True, methods=['post'])
    def mark_overdue(self, request, pk=None):
        """Mark an invoice as overdue."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_invoice_centre_id(invoice)):
            return centre_not_found('Invoice not found.')
        updated = billing_db.update_invoice(str(pk), {'status': 'Overdue'})
        return Response(updated)

    @action(detail=True, methods=['post'])
    def resend_email(self, request, pk=None):
        """Resend invoice email to parents (Req 23.5)."""
        invoice = billing_db.get_invoice(str(pk))
        if not invoice:
            return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_invoice_centre_id(invoice)):
            return centre_not_found('Invoice not found.')

        result = send_invoice_email(invoice)

        if result.get('reason') == 'no_contacts':
            return Response(
                {'detail': 'No parent email associated with this child.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if result.get('reason') == 'all_failed':
            errors = [r.get('error') for r in result.get('results', []) if r.get('error')]
            logger.warning(f"Invoice {invoice.get('id')} resend failed: {errors}")
            return Response(
                {'detail': 'Failed to send invoice email.', 'errors': errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        for entry in result.get('results', []):
            if entry['status'] == 'sent':
                billing_db.add_sent_to(str(pk), 'email', entry['email'])

        return Response({
            'detail': 'Invoice email sent.',
            'results': result.get('results', []),
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_summary(request):
    """Return invoice counts and totals grouped by status."""
    all_invoices = billing_db.list_invoices()

    access = get_user_access(request.user, request)
    accessible = access.accessible_centre_ids()
    if accessible is not None:
        centre_cache = {}
        filtered = []
        for inv in all_invoices:
            child_id = inv.get('child_id')
            if child_id not in centre_cache:
                centre_cache[child_id] = _child_centre_id(child_id) if child_id else None
            if centre_cache[child_id] in accessible:
                filtered.append(inv)
        all_invoices = filtered

    total_invoices = len(all_invoices)
    status_totals = {}
    for inv in all_invoices:
        s = inv.get('status', 'Draft')
        entry = status_totals.setdefault(s, {'count': 0, 'total_amount': 0.0})
        entry['count'] += 1
        entry['total_amount'] += float(inv.get('total_amount', 0) or 0)

    today_iso = date.today().isoformat()
    overdue_count = sum(
        1 for inv in all_invoices
        if inv.get('status') in ('Sent', 'Draft') and (inv.get('due_date') or '') < today_iso
    )

    return Response({
        'total_invoices': total_invoices,
        'overdue_count': overdue_count,
        'by_status': status_totals,
    })


class PurchaseViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if not child_pk:
            return Response([])
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_child_centre_id(child_pk)):
            return centre_not_found()
        purchases = billing_db.list_purchases(str(child_pk))
        return Response(purchases)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if not child_pk:
            return Response({'detail': 'A child is required to create a purchase.'}, status=status.HTTP_400_BAD_REQUEST)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_child_centre_id(child_pk)):
            return centre_not_found()
        purchase = billing_db.create_purchase(str(child_pk), request.data.copy())
        return Response(purchase, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        purchase = billing_db.get_purchase(str(kwargs['pk']))
        if not purchase:
            return Response({'detail': 'Purchase not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_child_centre_id(purchase.get('child_id'))):
            return centre_not_found('Purchase not found.')
        purchase = billing_db.update_purchase(str(kwargs['pk']), request.data)
        return Response(purchase)

    def destroy(self, request, *args, **kwargs):
        purchase = billing_db.get_purchase(str(kwargs['pk']))
        if not purchase:
            return Response({'detail': 'Purchase not found.'}, status=status.HTTP_404_NOT_FOUND)
        access = get_user_access(request.user, request)
        if not access.can_access_centre(_child_centre_id(purchase.get('child_id'))):
            return centre_not_found('Purchase not found.')
        billing_db.delete_purchase(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Centre-Level Invoice Endpoints (Req 29, 30)
# =============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centre_invoices(request, centre_pk):
    """
    List all invoices for a centre with filtering (Req 29.8-10).
    Query params: status, date_from, date_to, search
    """
    access = get_user_access(request.user, request)
    if not access.can_access_centre(centre_pk):
        return centre_not_found()

    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Summary stats over ALL centre invoices (before user filters)
    all_centre_invoices = _centre_invoice_set(centre_pk)

    # Resolve every invoice against its ledger once, then work from that.
    # The old stored `status` field could not express Part paid, went stale
    # the moment a payment landed, and counted a written-off invoice as money
    # received — so totals here were wrong as soon as anything was corrected.
    all_centre_invoices = _with_balances(all_centre_invoices)

    total_outstanding = sum(
        float(i['balance']['outstanding']) for i in all_centre_invoices)
    total_paid = sum(float(i['balance']['paid']) for i in all_centre_invoices)
    overdue_count = sum(
        1 for i in all_centre_invoices if i['balance']['status'] == ledger.OVERDUE)

    # Apply filters for the response list
    all_invoices = list(all_centre_invoices)

    inv_status = request.query_params.get('status')
    if inv_status and inv_status != 'All':
        # Accept the derived names ('part_paid') and the legacy display
        # names ('Part paid') callers may still be sending.
        wanted = inv_status.strip().lower().replace(' ', '_')
        all_invoices = [i for i in all_invoices if i['balance']['status'] == wanted]

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    if date_from:
        all_invoices = [i for i in all_invoices if (i.get('invoice_date') or '') >= date_from]
    if date_to:
        all_invoices = [i for i in all_invoices if (i.get('invoice_date') or '') <= date_to]

    search = request.query_params.get('search')
    if search:
        search_lower = search.lower()
        all_invoices = [
            i for i in all_invoices
            if search_lower in (i.get('student_name') or '').lower()
            or search_lower in (i.get('number') or '').lower()
        ]

    return Response({
        'summary': {
            'total_invoices': len(all_centre_invoices),
            'total_outstanding': total_outstanding,
            'total_paid': total_paid,
            'overdue_count': overdue_count,
        },
        'invoices': all_invoices,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_generate_data(request, centre_pk):
    """
    Return pre-populated data for invoice generation (Req 29.3, 29.7, 30.1-2).
    Returns centre details + list of children at this centre with parent info.
    """
    access = get_user_access(request.user, request)
    if not access.can_access_centre(centre_pk):
        return centre_not_found()

    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    bank = centre.get('bank_details', {}) or {}
    centre_data = {
        'centre_code': centre.get('system_id', ''),
        'centre_name': centre.get('name', ''),
        'centre_location': centre.get('city', ''),
        'full_address': f"{centre.get('street_address', '')}, {centre.get('city', '')}, {centre.get('postcode', '')}",
        'email': centre.get('email', ''),
        'phone': centre.get('phone', ''),
        'gst_number': centre.get('vat_number', ''),
        'bank_name': bank.get('bank_name', ''),
        'account_number': bank.get('account_number', ''),
        'ifsc_code': bank.get('ifsc_code', ''),
        'upi_id': bank.get('upi_id', ''),
        'account_holder_name': bank.get('account_holder_name', ''),
    }

    children = children_db.list_children(str(centre_pk))
    children_data = []
    for child in children:
        name_parts = [child.get('first_name', ''), child.get('middle_name', ''), child.get('last_name', '')]
        student_name = ' '.join(p for p in name_parts if p)
        # Find parent contact
        contacts = child.get('contacts', [])
        parent = next(
            (c for c in contacts if c.get('invite_as') in ('Parent', 'Guardian')),
            None
        )
        children_data.append({
            'id': child.get('id', ''),
            'student_name': student_name,
            'parent_name': parent.get('name', '') if parent else '',
            'parent_email': parent.get('email', '') if parent else '',
            'parent_phone': parent.get('phone', '') if parent else '',
            'session_name': child.get('session_name', ''),
            'date_of_birth': child.get('date_of_birth', ''),
        })

    bank_details_complete = bool(
        bank.get('account_holder_name') and
        bank.get('bank_name') and
        bank.get('account_number') and
        bank.get('ifsc_code')
    )

    return Response({
        'centre': centre_data,
        'children': children_data,
        'bank_details_complete': bank_details_complete,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centre_payments(request, centre_pk):
    """
    Payment tracking for a centre (Req 29.12).
    Returns invoices marked as paid with payment info.
    """
    access = get_user_access(request.user, request)
    if not access.can_access_centre(centre_pk):
        return centre_not_found()

    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    children_by_id = {c['id']: c for c in children_db.list_children(str(centre_pk))}

    # Real payment records, not invoices flagged paid. The old version could
    # only ever show one full-value payment per invoice, dated whenever the
    # row was last touched — so partial payments were invisible and the date
    # was whatever `updated_at` happened to be.
    #
    # Reached through _centre_invoice_set, not a child walk. Money taken
    # against an invoice raised without a child was recorded in the ledger and
    # counted in the balance, but never appeared here — so the invoice showed
    # as part paid while the Payments tab claimed nothing had been received.
    payments = []
    for inv in _centre_invoice_set(centre_pk):
        child = children_by_id.get(inv.get('child_id')) or {}
        student_name = (
            inv.get('student_name')
            or f"{child.get('first_name', '')} {child.get('last_name', '')}".strip()
        )
        for e in billing_db.list_ledger(inv['id']):
            if e.get('kind') != ledger.PAYMENT:
                continue
            payments.append({
                'id': e.get('id', ''),
                'invoice_id': inv.get('id', ''),
                'invoice_number': inv.get('number', ''),
                'student_name': student_name,
                'amount': float(e.get('amount') or 0),
                'method': e.get('method', ''),
                'payment_date': e.get('occurred_on', ''),
                'due_date': inv.get('due_date', ''),
            })

    payments.sort(key=lambda p: p['payment_date'], reverse=True)
    return Response({'payments': payments})


# =============================================================================
# Ledger — recording money and corrections against an invoice
# =============================================================================

# Each act asks its own permission. Front desk take payments all day and must
# not be able to raise, cancel, write off or refund; splitting these rows is
# the whole point (see billing/ledger.py).
LEDGER_PERMISSIONS = {
    ledger.PAYMENT: 'finance.manage_bill_payer_payments',
    ledger.CREDIT_NOTE: 'finance.manage_bill_payer_credits',
    ledger.WRITE_OFF: 'finance.write_off_invoices',
    ledger.REFUND: 'finance.refund_payments',
}


def _invoice_centre_id(invoice):
    """
    The centre an invoice is scoped to.

    The stamp comes first; the child is the fallback for rows written before
    it existed. Resolving through the child alone returns None for anything
    billed without one, and scope checks fail closed on None — so the invoice
    would list in the centre's history and then refuse to open.
    """
    return invoice.get('centre_id') or _child_centre_id(invoice.get('child_id'))


def _load_invoice_for(request, invoice_pk, permission):
    """
    Fetch an invoice and check the caller may perform `permission` at its
    centre. Returns (invoice, centre_id, error_response).
    """
    invoice = billing_db.get_invoice(str(invoice_pk))
    if not invoice:
        return None, None, Response(
            {'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)

    centre_id = _invoice_centre_id(invoice)
    access = get_user_access(request.user, request)
    if not access.can_access_centre(centre_id):
        # Not found rather than forbidden — otherwise the response confirms
        # an invoice exists at a centre the caller cannot see.
        return None, None, centre_not_found('Invoice not found.')
    if not access.can_edit(centre_id, permission):
        return None, None, permission_denied()
    return invoice, centre_id, None


def _balance_for(invoice):
    return ledger.compute_balance(invoice, billing_db.list_ledger(invoice['id']))


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def invoice_ledger(request, invoice_pk):
    """Every act recorded against this invoice, with the resulting balance."""
    invoice, _centre_id, error = _load_invoice_for(
        request, invoice_pk, 'finance.view_invoices')
    if error:
        return error

    entries = billing_db.list_ledger(invoice['id'])
    balance = ledger.compute_balance(invoice, entries)
    return Response({
        'invoice_id': invoice['id'],
        'entries': sorted(entries, key=lambda e: e.get('occurred_on') or ''),
        'balance': balance,
    })


def _record(request, invoice_pk, kind):
    invoice, _centre_id, error = _load_invoice_for(
        request, invoice_pk, LEDGER_PERMISSIONS[kind])
    if error:
        return error

    if invoice.get('cancelled_at'):
        return Response(
            {'detail': 'This invoice is cancelled — nothing can be recorded against it.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer_cls = KIND_SERIALIZERS[kind]
    serializer = (serializer_cls(data=request.data, kind=kind)
                  if serializer_cls is CorrectionSerializer
                  else serializer_cls(data=request.data))
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # A refund can only return money that actually came in.
    if kind == ledger.REFUND:
        balance = _balance_for(invoice)
        refundable = balance['paid'] - balance['refunded']
        if data['amount'] > refundable:
            return Response(
                {'amount': [f'Only {refundable} was received and not already refunded.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

    occurred = data.get('occurred_on')
    entry = billing_db.add_ledger_entry(
        invoice['id'], kind, data['amount'],
        reason=data.get('reason', ''),
        method=data.get('method', ''),
        occurred_on=occurred.isoformat() if occurred else date.today().isoformat(),
        recorded_by=str(getattr(request.user, 'id', '')),
    )
    return Response(
        {'entry': entry, 'balance': _balance_for(invoice)},
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def record_payment(request, invoice_pk):
    return _record(request, invoice_pk, ledger.PAYMENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def record_credit_note(request, invoice_pk):
    return _record(request, invoice_pk, ledger.CREDIT_NOTE)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def record_write_off(request, invoice_pk):
    return _record(request, invoice_pk, ledger.WRITE_OFF)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def record_refund(request, invoice_pk):
    return _record(request, invoice_pk, ledger.REFUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def cancel_invoice(request, invoice_pk):
    """Void an invoice. Never deletes it — the number and trail must survive."""
    invoice, _centre_id, error = _load_invoice_for(
        request, invoice_pk, 'finance.cancel_invoices')
    if error:
        return error

    if invoice.get('cancelled_at'):
        return Response(
            {'detail': 'This invoice is already cancelled.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = CancelInvoiceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reason = serializer.validated_data['reason']
    note = serializer.validated_data.get('note', '')

    updated = billing_db.cancel_invoice(
        invoice['id'],
        reason=f"{reason}: {note}" if note else reason,
        cancelled_by=str(getattr(request.user, 'id', '')),
    )
    return Response({'invoice': updated, 'balance': _balance_for(updated or invoice)})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def next_invoice_number(request):
    """
    Preview the next number without consuming it (INV-002).

    The form shows this on open. Allocation happens at generate, so a form
    opened and abandoned leaves no hole in the series.
    """
    return Response({'number': billing_db.peek_invoice_number(), 'preview': True})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def centre_debtors(request, centre_pk):
    """
    Who owes what, banded by how long it has been owed (INV-007 / INV-013).

    Debt that is merely visible gets discovered; debt that is bucketed gets
    worked. Settled, written-off and cancelled invoices are owed by nobody
    and never appear.
    """
    access = get_user_access(request.user, request)
    if not access.can_access_centre(centre_pk):
        return centre_not_found()
    if not access.can_view(centre_pk, 'finance.view_invoices'):
        return permission_denied()

    centre = centres_db.get_centre(str(centre_pk))
    if not centre:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    buckets = {b: {'count': 0, 'total': 0.0} for b in
               ('current', '0-30', '31-60', '61-90', '90+')}
    rows = []

    # Debt is owed to the centre, not to the child walk. An invoice raised
    # without naming a child is still money owed and has to be chased.
    children_by_id = {c['id']: c for c in children_db.list_children(str(centre_pk))}

    for inv in _centre_invoice_set(centre_pk):
        enriched = _with_balance(inv)
        balance = enriched['balance']
        outstanding = balance['outstanding']
        if outstanding <= 0:
            continue

        bucket = ledger.ageing_bucket(inv, outstanding)
        if not bucket:
            continue

        child = children_by_id.get(inv.get('child_id')) or {}
        amount = float(outstanding)
        buckets[bucket]['count'] += 1
        buckets[bucket]['total'] += amount
        rows.append({
            'invoice_id': inv.get('id', ''),
            'invoice_number': inv.get('number', ''),
            'child_id': child.get('id', ''),
            'student_name': (
                inv.get('student_name')
                or f"{child.get('first_name', '')} {child.get('last_name', '')}".strip()
            ),
            'due_date': inv.get('due_date', ''),
            'outstanding': amount,
            'status': balance['status'],
            'bucket': bucket,
        })

    # Oldest debt first — that is the order it should be worked in.
    order = {'90+': 0, '61-90': 1, '31-60': 2, '0-30': 3, 'current': 4}
    rows.sort(key=lambda r: (order[r['bucket']], -r['outstanding']))

    return Response({
        'buckets': buckets,
        'total_outstanding': sum(b['total'] for b in buckets.values()),
        'debtors': rows,
    })
