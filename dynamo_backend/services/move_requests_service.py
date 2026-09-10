"""
DynamoDB service for child move requests.

A centre asks to move one of its children to another centre; an admin decides.
The child does not move when the request is made — only when it is approved —
so this table is the whole of what exists in between.

The approval path needs one thing DynamoDB can give and a plain read-then-write
cannot: a claim that only one caller can win. `claim_for_decision` is a
conditional update, so two admins pressing Approve at the same moment cannot
both move the same child, and a retried request cannot move it twice.
"""

from datetime import datetime

from botocore.exceptions import ClientError

from ..service import DynamoDBService
from ..tables import CHILD_MOVE_REQUESTS_TABLE

PENDING = 'pending'
APPROVED = 'approved'
REJECTED = 'rejected'
# Transient: one caller has claimed a pending request and is partway through
# carrying it out. Never a resting state — the decision either completes and
# lands on approved/rejected, or is rolled back to pending.
PROCESSING = 'processing'

DECIDED = (APPROVED, REJECTED)


class MoveRequestConflict(RuntimeError):
    """The request was not pending — already decided, or being decided now."""


class MoveRequestsUnavailable(RuntimeError):
    """
    The move-requests table has not been provisioned in this environment.

    Its own type because it is an environment problem, not a request problem:
    a bare ResourceNotFoundException surfaces as a 500 that says nothing, and
    whoever hits it has no way to know a `create_dynamo_tables` run is all
    that is missing.
    """


def _missing_table(exc):
    return (
        isinstance(exc, ClientError)
        and exc.response['Error']['Code'] == 'ResourceNotFoundException'
    )


def _translating_missing_table(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ClientError as exc:
        if _missing_table(exc):
            raise MoveRequestsUnavailable(
                f"The {CHILD_MOVE_REQUESTS_TABLE} table does not exist. "
                f"Run: python manage.py create_dynamo_tables"
            ) from exc
        raise


class MoveRequestsDynamoService:
    def __init__(self):
        self.db = DynamoDBService(CHILD_MOVE_REQUESTS_TABLE)

    def create_request(self, child_id, from_centre_id, to_centre_id,
                       requested_by='', requested_by_id='', reason=''):
        return _translating_missing_table(self.db.create, {
            'child_id': str(child_id),
            'from_centre_id': str(from_centre_id),
            'to_centre_id': str(to_centre_id),
            'requested_by': requested_by,
            'requested_by_id': str(requested_by_id or ''),
            'reason': reason,
            'status': PENDING,
            'requested_at': datetime.utcnow().isoformat(),
        })

    def get(self, request_id):
        return _translating_missing_table(self.db.get, str(request_id))

    def list_all(self):
        return _translating_missing_table(self.db.list_all)

    def list_by_status(self, status):
        return _translating_missing_table(
            self.db.query_by_index, 'status-index', 'status', str(status))

    def list_for_child(self, child_id):
        return _translating_missing_table(
            self.db.query_by_index, 'child_id-index', 'child_id', str(child_id))

    def pending_for_child(self, child_id):
        """
        The open request for this child, if there is one.

        A child with a move already awaiting a decision must not collect a
        second one — two admins would then be deciding the same move against
        different destinations.
        """
        for row in self.list_for_child(child_id):
            if row.get('status') in (PENDING, PROCESSING):
                return row
        return None

    def claim_for_decision(self, request_id):
        """
        Take exclusive hold of a pending request, atomically.

        Raises MoveRequestConflict if it is not pending — which is what a
        second click, a retried request or a race with another admin looks
        like from here. The winner alone goes on to move the child.
        """
        try:
            response = self.db.table.update_item(
                Key={'id': str(request_id)},
                UpdateExpression='SET #s = :processing, #u = :now',
                ConditionExpression='attribute_exists(id) AND #s = :pending',
                ExpressionAttributeNames={'#s': 'status', '#u': 'updated_at'},
                ExpressionAttributeValues={
                    ':processing': PROCESSING,
                    ':pending': PENDING,
                    ':now': datetime.utcnow().isoformat(),
                },
                ReturnValues='ALL_NEW',
            )
        except ClientError as exc:
            if exc.response['Error']['Code'] == 'ConditionalCheckFailedException':
                raise MoveRequestConflict(
                    'This move request is no longer pending.') from exc
            if _missing_table(exc):
                raise MoveRequestsUnavailable(
                    f"The {CHILD_MOVE_REQUESTS_TABLE} table does not exist. "
                    f"Run: python manage.py create_dynamo_tables"
                ) from exc
            raise
        return response.get('Attributes', {})

    def release_claim(self, request_id):
        """
        Put a claimed request back to pending.

        Used when the work after the claim fails: the move did not happen, so
        the request must go back to awaiting a decision rather than sit
        stranded in `processing` where no admin can act on it.
        """
        return self.db.update(str(request_id), {'status': PENDING})

    def mark_decided(self, request_id, status, decided_by='', decided_by_id='',
                     note=''):
        """Record the outcome and who is answerable for it."""
        return self.db.update(str(request_id), {
            'status': status,
            'decided_by': decided_by,
            'decided_by_id': str(decided_by_id or ''),
            'decided_at': datetime.utcnow().isoformat(),
            'decision_note': note,
        })
