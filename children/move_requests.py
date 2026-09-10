"""
Moving a child from one centre to another.

Three rules shape everything here.

The child does not move when the request is made. A centre asks; the record
that is written is a pending request, and the child's `centre_id` is untouched
until a Global Admin says yes. Anything else lets a centre move children by
itself and calls it an approval workflow.

Only a Global Admin decides. Not the centre that asked, not a centre-scoped
role however many permissions it has been given, and not a Centre Manager or
an ordinary portal admin either — approving is an organisation-level act, so
it asks for the organisation's own administrators: root, or a holder of the
Super Admin global role (global_access.capabilities.is_global_admin).

The approval is all-or-nothing. DynamoDB has no transaction spanning the
child, its invoices and this request, so the effect is built instead: one
caller claims the pending request with a conditional write, and if any later
step fails, everything already done is put back and the request returns to
pending. A child is never left half-moved, and a rejected request changes
nothing at all.

There are two doors to a decision — the portal and the link in the email —
and they open onto the same code (_carry_out_approval / _carry_out_rejection),
so a decision made from an inbox is exactly the decision made from the queue.
"""

import logging

from django.core import signing
from rest_framework import status
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from billing.transfers import (
    clear_child_invoices_for_move, old_centre_invoices, reattach_child_invoices,
)
from billing.ledger import compute_balance
from dynamo_backend.services import auth_db, billing_db, centres_db, children_db, move_requests_db
from dynamo_backend.services.children_service import is_archived
from dynamo_backend.services.move_requests_service import (
    APPROVED, MoveRequestConflict, MoveRequestsUnavailable, PENDING, PROCESSING,
    REJECTED,
)
from global_access.capabilities import email_is_global_admin, is_global_admin
from notifications.mailer import send_move_decision_email, send_move_request_email
from notifications.tokens import read_move_action_token
from roles.access import centre_not_found, get_user_access, permission_denied
from schindia_auth.permissions import IsApprovedUser

logger = logging.getLogger(__name__)

# Requesting a move is a centre-level act on a child, so it asks the
# centre-scoped permission that already means exactly that.
REQUEST_PERMISSION = 'children.transfer_sites'

LIST_STATUSES = (PENDING, PROCESSING, APPROVED, REJECTED)

EMAIL_ACTIONS = ('approve', 'reject')


def _actor(request):
    user = request.user
    return getattr(user, 'email', '') or str(getattr(user, 'id', ''))


def _unavailable(exc):
    """
    The move-requests table has not been provisioned in this environment.

    503 rather than 500, and the message names the command that fixes it. An
    environment missing a table is not a broken request, and nobody should
    have to read a stack trace to find out that one command is all it needs.
    """
    logger.error("Child moves unavailable: %s", exc)
    return Response(
        {
            'detail': (
                'Child moves are not set up in this environment yet. An '
                'administrator needs to run: python manage.py create_dynamo_tables'
            ),
            'reason': 'not_provisioned',
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _is_org_admin(request):
    """
    Whether the caller may decide move requests: a Global Admin.

    Root, or a holder of the Super Admin global role. Deliberately narrower
    than roles.access `unrestricted`, which every approved portal user has —
    a centre owner or Centre Manager can see every centre, but deciding a
    child's move is the organisation's call, not a centre's.
    """
    return is_global_admin(request.user, request)


def _decorate(move_request):
    """
    Add the names a queue has to show.

    Read at response time rather than stored on the request, so a centre
    renamed after the request was raised does not display under its old name.
    """
    if not move_request:
        return move_request

    child = children_db.get_child(str(move_request.get('child_id') or ''))
    from_centre = centres_db.get_centre(str(move_request.get('from_centre_id') or ''))
    to_centre = centres_db.get_centre(str(move_request.get('to_centre_id') or ''))

    enriched = dict(move_request)
    enriched['child_name'] = (
        f"{(child or {}).get('first_name', '')} {(child or {}).get('last_name', '')}".strip()
    )
    enriched['child_system_id'] = (child or {}).get('system_id', '')
    enriched['from_centre_name'] = (from_centre or {}).get('name', '')
    enriched['to_centre_name'] = (to_centre or {}).get('name', '')
    return enriched


def _decorate_bulk(rows):
    """
    Bulk decorate multiple move requests to prevent N+1 DynamoDB queries.
    """
    if not rows:
        return []

    child_ids = set()
    for r in rows:
        if r.get('child_id'):
            child_ids.add(str(r['child_id']))

    centre_ids = set()
    for r in rows:
        if r.get('from_centre_id'):
            centre_ids.add(str(r['from_centre_id']))
        if r.get('to_centre_id'):
            centre_ids.add(str(r['to_centre_id']))

    # Fetch centres individually since list_centres() might not be mocked in all tests
    all_centres = {}
    for cid in centre_ids:
        all_centres[cid] = centres_db.get_centre(cid)

    # Fetch unique children
    children_map = {}
    for cid in child_ids:
        children_map[cid] = children_db.get_child(cid)

    results = []
    for r in rows:
        child = children_map.get(str(r.get('child_id') or ''))
        from_centre = all_centres.get(str(r.get('from_centre_id') or ''))
        to_centre = all_centres.get(str(r.get('to_centre_id') or ''))

        enriched = dict(r)
        enriched['child_name'] = (
            f"{(child or {}).get('first_name', '')} {(child or {}).get('last_name', '')}".strip()
        )
        enriched['child_system_id'] = (child or {}).get('system_id', '')
        enriched['from_centre_name'] = (from_centre or {}).get('name', '')
        enriched['to_centre_name'] = (to_centre or {}).get('name', '')
        results.append(enriched)

    return results


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def child_move_requests(request, child_pk):
    """
    GET  — this child's move requests, newest first.
    POST — ask to move this child to another centre. Creates a PENDING
           request and emails the Global Admins. The child does not move.
    """
    child = children_db.get_child(str(child_pk))
    if not child:
        return Response({'detail': 'Child not found.'},
                        status=status.HTTP_404_NOT_FOUND)

    from_centre_id = child.get('centre_id')
    access = get_user_access(request.user, request)
    if not access.can_access_centre(from_centre_id):
        return centre_not_found('Child not found.')

    if request.method == 'GET':
        if not access.can_view(from_centre_id, 'children.view_info'):
            return permission_denied()
        try:
            rows = move_requests_db.list_for_child(str(child_pk))
        except MoveRequestsUnavailable as exc:
            return _unavailable(exc)
        rows.sort(key=lambda r: r.get('requested_at') or '', reverse=True)
        return Response(_decorate_bulk(rows))

    if not access.can_edit(from_centre_id, REQUEST_PERMISSION):
        return permission_denied()

    to_centre_id = str(request.data.get('to_centre_id') or
                       request.data.get('centre_id') or '').strip()
    if not to_centre_id:
        return Response({'to_centre_id': ['A destination centre is required.']},
                        status=status.HTTP_400_BAD_REQUEST)
    if to_centre_id == str(from_centre_id):
        return Response(
            {'to_centre_id': ['That is the centre the child is already at.']},
            status=status.HTTP_400_BAD_REQUEST)

    destination = centres_db.get_centre(to_centre_id)
    if not destination:
        return Response({'to_centre_id': ['That centre does not exist.']},
                        status=status.HTTP_400_BAD_REQUEST)

    if is_archived(child):
        return Response(
            {'detail': 'This child is archived. Restore them before moving them.'},
            status=status.HTTP_400_BAD_REQUEST)

    # Check for unpaid invoices
    from_centre_id = child.get('centre_id')
    outstanding = _child_outstanding_balance(child_pk, from_centre_id)
    if outstanding > 0:
        return Response(
            {'detail': f'This student cannot be transferred because they have an outstanding balance of ₹{outstanding:g} at this centre. All invoices must be settled first.'},
            status=status.HTTP_400_BAD_REQUEST)

    # One open request per child. A second one would have two admins deciding
    # the same move against different destinations.
    try:
        existing = move_requests_db.pending_for_child(str(child_pk))
    except MoveRequestsUnavailable as exc:
        return _unavailable(exc)
    if existing:
        return Response(
            {'detail': 'A move request for this child is already awaiting a decision.',
             'move_request': _decorate(existing)},
            status=status.HTTP_409_CONFLICT)

    try:
        created = move_requests_db.create_request(
            child_id=str(child_pk),
            from_centre_id=str(from_centre_id),
            to_centre_id=to_centre_id,
            requested_by=_actor(request),
            requested_by_id=str(request.user.id),
            reason=str(request.data.get('reason') or '').strip(),
        )
    except MoveRequestsUnavailable as exc:
        return _unavailable(exc)

    from_centre = centres_db.get_centre(str(from_centre_id)) if from_centre_id else None
    delivery = send_move_request_email(created, child, from_centre, destination)

    payload = _decorate(created)
    # Say whether a Global Admin was actually told. The request stands either
    # way, but a queue nobody has been pointed at is a child waiting indefinitely.
    payload['admin_notified'] = {
        'sent': delivery.get('sent', False),
        'reason': delivery.get('reason'),
    }
    return Response(payload, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def move_requests_list(request):
    """
    The Global Admin queue. `?status=pending` (the default) narrows it; `all`
    shows every request ever raised.
    """
    if not _is_org_admin(request):
        return permission_denied('Only a Global Admin can review child moves.')

    wanted = (request.query_params.get('status') or PENDING).strip().lower()
    if wanted != 'all' and wanted not in LIST_STATUSES:
        return Response(
            {'status': ['Must be one of: ' + ', '.join(LIST_STATUSES + ('all',))]},
            status=status.HTTP_400_BAD_REQUEST)

    try:
        if wanted == 'all':
            rows = move_requests_db.list_all()
        else:
            rows = move_requests_db.list_by_status(wanted)
            if wanted == PENDING:
                # A request being decided right now is still outstanding from
                # the queue's point of view — leaving it out would look done.
                rows = rows + move_requests_db.list_by_status(PROCESSING)
    except MoveRequestsUnavailable as exc:
        return _unavailable(exc)

    rows.sort(key=lambda r: r.get('requested_at') or '', reverse=True)
    return Response(_decorate_bulk(rows))


# ── Carrying out a decision ─────────────────────────────────────────
# One implementation for both the portal and the email link. The caller has
# already established *who* is deciding; these establish *what happens*.


def _carry_out_approval(pk, decided_by, decided_by_id, note):
    """
    Approve a move: the child changes centre and the old centre's invoices
    come off them. Returns the Response to send.

    The claim below is the only place two simultaneous approvals can be
    separated, so everything that changes state happens after it, and anything
    that fails afterwards is undone before the request goes back to pending.
    """
    pk = str(pk)
    try:
        move_request = move_requests_db.get(pk)
    except MoveRequestsUnavailable as exc:
        return _unavailable(exc)
    if not move_request:
        return Response({'detail': 'Move request not found.'},
                        status=status.HTTP_404_NOT_FOUND)

    child_id = str(move_request.get('child_id') or '')
    from_centre_id = str(move_request.get('from_centre_id') or '')
    to_centre_id = str(move_request.get('to_centre_id') or '')

    child = children_db.get_child(child_id)
    if not child:
        return Response({'detail': 'The child on this request no longer exists.'},
                        status=status.HTTP_409_CONFLICT)
    destination = centres_db.get_centre(to_centre_id)
    if not destination:
        return Response({'detail': 'The requested centre no longer exists.'},
                        status=status.HTTP_409_CONFLICT)
    # The world may have moved since the request was raised. Approving a move
    # away from a centre the child has already left would send them somewhere
    # nobody asked for.
    if str(child.get('centre_id')) != from_centre_id:
        return Response(
            {'detail': 'This child is no longer at the centre the request was raised from.'},
            status=status.HTTP_409_CONFLICT)

    try:
        move_requests_db.claim_for_decision(pk)
    except MoveRequestConflict:
        return Response(
            {'detail': 'This move request has already been decided.',
             'move_request': _decorate(move_requests_db.get(pk))},
            status=status.HTTP_409_CONFLICT)

    detached = []
    cancelled_enrolments = []
    removed_from_slots = []
    child_moved = False
    try:
        children_db.update_child(child_id, {'centre_id': to_centre_id})
        child_moved = True
        detached = clear_child_invoices_for_move(child_id, from_centre_id, pk)
        
        # Cancel all active enrollments at the old center
        from datetime import datetime
        from dynamo_backend.services import sessions_db
        
        now_iso = datetime.utcnow().isoformat()
        active_enrolments = children_db.list_enrolments(child_id, include_cancelled=False)
        for e in active_enrolments:
            children_db.update_enrolment(e['id'], {'cancelled_at': now_iso})
            cancelled_enrolments.append(e['id'])
            
        # Remove child from all slots at the old center (in case they lack explicit enrolment records)
        old_centre_slots = sessions_db.list_slots(from_centre_id)
        for slot in old_centre_slots:
            c_ids = slot.get('child_ids', [])
            if child_id in c_ids:
                c_ids.remove(child_id)
                sessions_db.update_slot(slot['id'], {'child_ids': c_ids})
                removed_from_slots.append(slot['id'])
        decided = move_requests_db.mark_decided(
            pk, APPROVED, decided_by=decided_by, decided_by_id=decided_by_id,
            note=note,
        )
    except Exception:
        logger.exception("Move %s failed partway; rolling back", pk)
        if detached:
            reattach_child_invoices(child_id, detached)
        
        # Rollback enrollments and slots
        for e_id in cancelled_enrolments:
            children_db.update_enrolment(e_id, {'cancelled_at': None})
            
        from dynamo_backend.services import sessions_db
        for s_id in removed_from_slots:
            children_db._add_child_to_slot(s_id, child_id)
            
        if child_moved:
            children_db.update_child(child_id, {'centre_id': from_centre_id})
        move_requests_db.release_claim(pk)
        return Response(
            {'detail': 'The move could not be completed. Nothing was changed.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    from_centre = centres_db.get_centre(from_centre_id) if from_centre_id else None
    # Best-effort: the move is done and recorded, so a mail failure here is
    # worth logging and nothing more.
    send_move_decision_email(decided, child, from_centre, destination, approved=True)

    return Response({
        'detail': 'Move approved.',
        'move_request': _decorate(decided),
        'child': children_db.get_child(child_id),
        'invoices_cleared': detached,
    })


def _carry_out_rejection(pk, decided_by, decided_by_id, note):
    """
    Reject a move. The child stays where they are and no invoice is touched —
    a rejection is the absence of a change, not a different one.
    """
    pk = str(pk)
    try:
        move_request = move_requests_db.get(pk)
    except MoveRequestsUnavailable as exc:
        return _unavailable(exc)
    if not move_request:
        return Response({'detail': 'Move request not found.'},
                        status=status.HTTP_404_NOT_FOUND)

    try:
        move_requests_db.claim_for_decision(pk)
    except MoveRequestConflict:
        return Response(
            {'detail': 'This move request has already been decided.',
             'move_request': _decorate(move_requests_db.get(pk))},
            status=status.HTTP_409_CONFLICT)

    decided = move_requests_db.mark_decided(
        pk, REJECTED, decided_by=decided_by, decided_by_id=decided_by_id,
        note=note,
    )

    child = children_db.get_child(str(move_request.get('child_id') or ''))
    from_centre = centres_db.get_centre(str(move_request.get('from_centre_id') or ''))
    to_centre = centres_db.get_centre(str(move_request.get('to_centre_id') or ''))
    send_move_decision_email(decided, child, from_centre, to_centre, approved=False)

    return Response({
        'detail': 'Move rejected.',
        'move_request': _decorate(decided),
    })


def _note(data):
    return str((data or {}).get('note') or '').strip()


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def approve_move_request(request, pk):
    """Approve from the portal. Global Admins only."""
    if not _is_org_admin(request):
        return permission_denied('Only a Global Admin can approve child moves.')
    return _carry_out_approval(
        pk, decided_by=_actor(request), decided_by_id=str(request.user.id),
        note=_note(request.data),
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def reject_move_request(request, pk):
    """Reject from the portal. Global Admins only."""
    if not _is_org_admin(request):
        return permission_denied('Only a Global Admin can reject child moves.')
    return _carry_out_rejection(
        pk, decided_by=_actor(request), decided_by_id=str(request.user.id),
        note=_note(request.data),
    )


# ── Deciding from the email ─────────────────────────────────────────


def _email_actor(email):
    """
    Who to record as having decided from the email.

    The address, marked so the audit trail says how the decision arrived, and
    the portal user id behind it when there is one — best-effort, because a
    Super Admin need not have a portal login to hold the role.
    """
    decided_by = f"{email} (Email)"
    decided_by_id = ''
    try:
        user = auth_db.get_user_by_email(email)
        if user:
            decided_by_id = str(user.get('id') or '')
    except Exception:
        logger.warning("Could not resolve a portal user for %s", email, exc_info=True)
    return decided_by, decided_by_id


def _resolve_email_token(raw_token):
    """
    Turn the token from an email link into (payload, move_request), or a
    Response saying why it cannot be used.

    Refused in this order: no token, a forged or altered one, an expired one,
    one for an address that is not (or is no longer) a Global Admin, and one
    for a request that no longer exists.
    """
    raw_token = (raw_token or '').strip()
    if not raw_token:
        return None, Response(
            {'detail': 'This link is missing its token.', 'reason': 'missing_token'},
            status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = read_move_action_token(raw_token)
    except signing.SignatureExpired:
        return None, Response(
            {'detail': 'This link has expired. Decide the move in the admin '
                       'portal under Global settings → Child moves.',
             'reason': 'expired'},
            status=status.HTTP_410_GONE)
    except signing.BadSignature:
        return None, Response(
            {'detail': 'This link is not valid.', 'reason': 'invalid'},
            status=status.HTTP_400_BAD_REQUEST)

    email = str(payload.get('email') or '').strip().lower()
    if not email_is_global_admin(email):
        return None, Response(
            {'detail': 'This link belongs to an address that is not a Global Admin.',
             'reason': 'not_global_admin'},
            status=status.HTTP_403_FORBIDDEN)

    try:
        move_request = move_requests_db.get(str(payload.get('move_request_id')))
    except MoveRequestsUnavailable as exc:
        return None, _unavailable(exc)
    if not move_request:
        return None, Response(
            {'detail': 'Move request not found.', 'reason': 'not_found'},
            status=status.HTTP_404_NOT_FOUND)

    return {'email': email, 'move_request_id': str(move_request['id'])}, None


def _invoice_count(move_request):
    """How many invoices approving would clear; None if that cannot be told."""
    try:
        return len(old_centre_invoices(
            str(move_request.get('child_id') or ''),
            str(move_request.get('from_centre_id') or ''),
        ))
    except Exception:
        logger.warning("Could not count invoices for move %s",
                       move_request.get('id'), exc_info=True)
        return None


def _child_outstanding_balance(child_id, centre_id):
    """
    Returns the total outstanding balance for a child's invoices at a given centre.
    """
    from dynamo_backend.services import billing_db
    from billing.ledger import compute_balance
    invoices = old_centre_invoices(child_id, centre_id)
    total_outstanding = 0
    for invoice in invoices:
        entries = billing_db.list_ledger(invoice['id'])
        balance = compute_balance(invoice, entries)
        total_outstanding += float(balance.get('outstanding', 0))
    return total_outstanding


@api_view(['GET', 'POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def email_move_decision(request):
    """
    The endpoint behind the email links, with the signed token as the only
    credential. No session is involved — a Global Admin opening the email on
    their phone should not have to log in first — and no Authorization header
    is read, so a stale one in the browser cannot turn a good link into a 401.

    GET  — what the link is about: the request, its current status, and who
           the token was issued to. Reads nothing but the token; decides
           nothing. This is the request a mail scanner makes, and it is
           harmless.
    POST — {token, action: approve|reject, note?}. Carries out the decision,
           through the same code the portal uses, recorded against the
           recipient's address.
    """
    if request.method == 'GET':
        raw_token = request.query_params.get('token')
    else:
        raw_token = request.data.get('token') or request.query_params.get('token')

    resolved, error = _resolve_email_token(raw_token)
    if error is not None:
        return error
    email = resolved['email']
    pk = resolved['move_request_id']

    if request.method == 'GET':
        move_request = move_requests_db.get(pk)
        payload = _decorate(move_request)
        payload['decider_email'] = email
        payload['invoice_count'] = _invoice_count(move_request)
        return Response(payload)

    action = str(request.data.get('action') or '').strip().lower()
    if action not in EMAIL_ACTIONS:
        return Response(
            {'action': ['Must be one of: ' + ', '.join(EMAIL_ACTIONS)]},
            status=status.HTTP_400_BAD_REQUEST)

    decided_by, decided_by_id = _email_actor(email)
    note = _note(request.data)
    if action == 'approve':
        return _carry_out_approval(pk, decided_by, decided_by_id, note)
    return _carry_out_rejection(pk, decided_by, decided_by_id, note)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def child_move_preview(request, child_pk):
    """
    What approving a move for this child would affect.

    Lets the centre raising the request see which invoices would come off the
    child before it asks, rather than discovering it afterwards.
    """
    child = children_db.get_child(str(child_pk))
    if not child:
        return Response({'detail': 'Child not found.'},
                        status=status.HTTP_404_NOT_FOUND)

    access = get_user_access(request.user, request)
    if not access.can_access_centre(child.get('centre_id')):
        return centre_not_found('Child not found.')
    if not access.can_view(child.get('centre_id'), 'children.view_info'):
        return permission_denied()

    invoices = old_centre_invoices(str(child_pk), str(child.get('centre_id') or ''))

    # An unprovisioned table must not stop the dialog opening. The invoice
    # figures are true and worth showing either way; only "is one already
    # pending" is unknown, and the flag says so rather than implying no.
    try:
        pending = _decorate(move_requests_db.pending_for_child(str(child_pk)))
        available = True
    except MoveRequestsUnavailable as exc:
        logger.error("Child moves unavailable: %s", exc)
        pending, available = None, False
        
    outstanding = _child_outstanding_balance(str(child_pk), str(child.get('centre_id') or ''))

    return Response({
        'child_id': str(child_pk),
        'from_centre_id': child.get('centre_id'),
        'invoice_count': len(invoices),
        'outstanding_balance': outstanding,
        'invoices': [
            {'id': i['id'], 'number': i.get('number', ''),
             'total_amount': i.get('total_amount', '0')}
            for i in invoices
        ],
        'pending_request': pending,
        'move_requests_available': available,
    })
