"""
The claim that makes an approval safe.

DynamoDB has no transaction spanning the child, its invoices and the request,
so the guarantee is built out of one conditional write: exactly one caller can
take a pending request. Everything that changes state happens after that, and
is undone if a later step fails.
"""
from unittest.mock import MagicMock

from botocore.exceptions import ClientError
from django.test import SimpleTestCase

from dynamo_backend.services.move_requests_service import (
    APPROVED, MoveRequestConflict, MoveRequestsDynamoService, PENDING,
    PROCESSING, REJECTED,
)

CHILD_ID = "11111111-1111-1111-1111-111111111111"
FROM_CENTRE = "22222222-2222-2222-2222-222222222222"
TO_CENTRE = "88888888-8888-8888-8888-888888888888"
REQUEST_ID = "44444444-4444-4444-4444-444444444444"


def conditional_check_failed():
    return ClientError(
        {'Error': {'Code': 'ConditionalCheckFailedException',
                   'Message': 'The conditional request failed'}},
        'UpdateItem',
    )


class ClaimForDecisionTests(SimpleTestCase):
    def setUp(self):
        self.service = MoveRequestsDynamoService()
        self.service.db = MagicMock()

    def test_a_pending_request_can_be_claimed(self):
        self.service.db.table.update_item.return_value = {
            'Attributes': {'id': REQUEST_ID, 'status': PROCESSING}}

        claimed = self.service.claim_for_decision(REQUEST_ID)

        self.assertEqual(claimed['status'], PROCESSING)

    def test_the_claim_is_conditional_on_the_request_still_being_pending(self):
        # Without the condition two admins could both move the same child.
        self.service.db.table.update_item.return_value = {'Attributes': {}}

        self.service.claim_for_decision(REQUEST_ID)

        kwargs = self.service.db.table.update_item.call_args.kwargs
        self.assertIn('ConditionExpression', kwargs)
        self.assertEqual(kwargs['ExpressionAttributeValues'][':pending'], PENDING)

    def test_a_request_that_is_no_longer_pending_raises_a_conflict(self):
        self.service.db.table.update_item.side_effect = conditional_check_failed()

        with self.assertRaises(MoveRequestConflict):
            self.service.claim_for_decision(REQUEST_ID)

    def test_any_other_dynamo_error_is_not_mistaken_for_a_conflict(self):
        # A throttle is a retryable outage, not "somebody already decided".
        self.service.db.table.update_item.side_effect = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException',
                       'Message': 'slow down'}}, 'UpdateItem')

        with self.assertRaises(ClientError):
            self.service.claim_for_decision(REQUEST_ID)

    def test_releasing_a_claim_returns_it_to_pending(self):
        # A request stranded in `processing` is one no admin can act on.
        self.service.release_claim(REQUEST_ID)

        self.service.db.update.assert_called_once_with(
            REQUEST_ID, {'status': PENDING})


class MoveRequestRecordTests(SimpleTestCase):
    def setUp(self):
        self.service = MoveRequestsDynamoService()
        self.service.db = MagicMock()

    def test_a_new_request_starts_pending(self):
        self.service.create_request(CHILD_ID, FROM_CENTRE, TO_CENTRE,
                                    requested_by='manager@shichida.local')

        written = self.service.db.create.call_args[0][0]
        self.assertEqual(written['status'], PENDING)
        self.assertEqual(written['child_id'], CHILD_ID)
        self.assertEqual(written['from_centre_id'], FROM_CENTRE)
        self.assertEqual(written['to_centre_id'], TO_CENTRE)
        self.assertTrue(written['requested_at'])

    def test_a_decision_records_who_made_it_and_when(self):
        self.service.mark_decided(REQUEST_ID, APPROVED,
                                  decided_by='admin@shichida.local',
                                  decided_by_id='admin-1', note='Relocated')

        written = self.service.db.update.call_args[0][1]
        self.assertEqual(written['status'], APPROVED)
        self.assertEqual(written['decided_by'], 'admin@shichida.local')
        self.assertEqual(written['decision_note'], 'Relocated')
        self.assertTrue(written['decided_at'])

    def test_an_open_request_is_found_whether_pending_or_being_decided(self):
        for state in (PENDING, PROCESSING):
            with self.subTest(state=state):
                self.service.db.query_by_index.return_value = [
                    {'id': REQUEST_ID, 'status': state}]
                self.assertIsNotNone(self.service.pending_for_child(CHILD_ID))

    def test_a_decided_request_does_not_block_a_new_one(self):
        # A rejected move must be re-askable; an approved one is history.
        for state in (APPROVED, REJECTED):
            with self.subTest(state=state):
                self.service.db.query_by_index.return_value = [
                    {'id': REQUEST_ID, 'status': state}]
                self.assertIsNone(self.service.pending_for_child(CHILD_ID))

    def test_a_child_with_no_history_has_no_open_request(self):
        self.service.db.query_by_index.return_value = []

        self.assertIsNone(self.service.pending_for_child(CHILD_ID))


class TableRegistrationTests(SimpleTestCase):
    def test_the_move_requests_table_is_provisioned_with_both_indexes(self):
        # A queue that has to scan every request ever made would degrade as
        # the archive grows; the status index is what keeps it a query.
        from dynamo_backend.setup_tables import TABLE_DEFINITIONS
        from dynamo_backend.tables import CHILD_MOVE_REQUESTS_TABLE

        definition = next(
            (d for d in TABLE_DEFINITIONS
             if d['TableName'] == CHILD_MOVE_REQUESTS_TABLE), None)

        self.assertIsNotNone(definition)
        self.assertEqual(
            sorted(i['IndexName'] for i in definition['GlobalSecondaryIndexes']),
            ['child_id-index', 'status-index'],
        )

    def test_the_service_singleton_is_exported(self):
        from dynamo_backend.services import move_requests_db

        self.assertIsInstance(move_requests_db, MoveRequestsDynamoService)
