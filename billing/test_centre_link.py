"""
An invoice must know which centre raised it.

The bug these cover: invoices were reachable only by walking a centre's
children, so anything billed without naming a child — the ordinary case when
generating from the centre's own Invoices tab — never appeared in Invoice
History, at that centre or any other. It was stored, numbered, and lost.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

CENTRE_ID = "22222222-2222-2222-2222-222222222222"
OTHER_CENTRE = "44444444-4444-4444-4444-444444444444"
CHILD_ID = "55555555-5555-5555-5555-555555555555"


class FakeUser:
    def __init__(self):
        self.id = "33333333-3333-3333-3333-333333333333"
        self.pk = self.id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = "approved"
        self.role = "staff"
        self.email = "front.desk@shichida.local"


def access_to(*centre_ids):
    a = MagicMock()
    a.can_access_centre.side_effect = lambda c: str(c) in {str(x) for x in centre_ids}
    a.can_view.return_value = True
    a.can_edit.return_value = True
    a.accessible_centre_ids.return_value = list(centre_ids)
    return a


@patch("billing.views.send_invoice_email", MagicMock())
@patch("billing.views.get_user_access")
@patch("billing.views.children_db")
@patch("billing.views.billing_db")
class InvoiceCentreStampTests(SimpleTestCase):
    """Creating an invoice records the centre it was raised at."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _post(self, payload):
        return self.client.post("/api/v1/invoices/", payload, format="json")

    def test_stamps_the_centre_it_was_raised_at(self, db, kids, access):
        access.return_value = access_to(CENTRE_ID)
        db.allocate_invoice_number.return_value = "BA260001"
        db.create_invoice.side_effect = lambda d: dict(d, id="inv-1")

        res = self._post({"centreId": CENTRE_ID, "studentName": "Walk-in"})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        stored = db.create_invoice.call_args[0][0]
        self.assertEqual(stored["centre_id"], CENTRE_ID)

    def test_falls_back_to_the_childs_centre(self, db, kids, access):
        # Raised from a child's profile: the centre is implied, not posted.
        access.return_value = access_to(CENTRE_ID)
        kids.get_child.return_value = {"id": CHILD_ID, "centre_id": CENTRE_ID}
        db.allocate_invoice_number.return_value = "BA260002"
        db.create_invoice.side_effect = lambda d: dict(d, id="inv-2")

        res = self._post({"childId": CHILD_ID})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(db.create_invoice.call_args[0][0]["centre_id"], CENTRE_ID)

    def test_refuses_a_centre_the_caller_cannot_see(self, db, kids, access):
        # The centre arrives in the payload, so it cannot be taken on trust.
        access.return_value = access_to(CENTRE_ID)
        db.allocate_invoice_number.return_value = "BA260003"

        res = self._post({"centreId": OTHER_CENTRE})

        self.assertIn(res.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        db.create_invoice.assert_not_called()

    def test_never_stores_an_empty_centre_id(self, db, kids, access):
        # An empty string is not a legal GSI key and fails the write outright.
        access.return_value = access_to(CENTRE_ID)
        kids.get_child.return_value = None
        db.allocate_invoice_number.return_value = "BA260004"
        db.create_invoice.side_effect = lambda d: dict(d, id="inv-4")

        res = self._post({"centreId": "", "studentName": "No centre"})

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("centre_id", db.create_invoice.call_args[0][0])


@patch("billing.views.get_user_access")
@patch("billing.views.centres_db")
@patch("billing.views.children_db")
@patch("billing.views.billing_db")
class CentreInvoiceListingTests(SimpleTestCase):
    """The centre listing finds invoices by centre, not only via children."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=FakeUser())

    def _wire(self, db, kids, centres, access, by_centre, by_child=None):
        access.return_value = access_to(CENTRE_ID)
        centres.get_centre.return_value = {"id": CENTRE_ID, "name": "Sunshine"}
        kids.list_children.return_value = (
            [{"id": CHILD_ID, "first_name": "Alice", "last_name": "A"}] if by_child else []
        )
        kids.get_child.return_value = {"id": CHILD_ID, "centre_id": CENTRE_ID}
        db.list_ledger.return_value = []

        def _list(child_id=None, user_id=None, centre_id=None):
            if centre_id:
                return list(by_centre)
            if child_id:
                return list(by_child or [])
            return []

        db.list_invoices.side_effect = _list

    def test_shows_an_invoice_raised_without_a_child(self, db, kids, centres, access):
        # The exact case that vanished: billed from the centre tab, no child.
        walkin = {"id": "inv-walkin", "number": "BA260010", "centre_id": CENTRE_ID,
                  "child_id": None, "total_amount": "5000", "due_date": "2099-01-01"}
        self._wire(db, kids, centres, access, by_centre=[walkin])

        res = self.client.get(f"/api/v1/centres/{CENTRE_ID}/invoices/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        numbers = [i.get("number") for i in res.data["invoices"]]
        self.assertIn("BA260010", numbers)

    def test_counts_a_childless_invoice_in_the_summary(self, db, kids, centres, access):
        walkin = {"id": "inv-walkin", "number": "BA260010", "centre_id": CENTRE_ID,
                  "child_id": None, "total_amount": "5000", "due_date": "2099-01-01"}
        self._wire(db, kids, centres, access, by_centre=[walkin])

        res = self.client.get(f"/api/v1/centres/{CENTRE_ID}/invoices/")

        # Billed money that is invisible in the totals is worse than useless.
        self.assertEqual(float(res.data["summary"]["total_outstanding"]), 5000.0)

    def test_lists_an_invoice_reachable_both_ways_once(self, db, kids, centres, access):
        both = {"id": "inv-both", "number": "BA260011", "centre_id": CENTRE_ID,
                "child_id": CHILD_ID, "total_amount": "100", "due_date": "2099-01-01"}
        self._wire(db, kids, centres, access, by_centre=[both], by_child=[both])

        res = self.client.get(f"/api/v1/centres/{CENTRE_ID}/invoices/")

        ids = [i.get("id") for i in res.data["invoices"]]
        self.assertEqual(ids.count("inv-both"), 1, "the two routes must dedupe by id")

    def test_still_finds_older_invoices_that_predate_the_stamp(self, db, kids, centres, access):
        # Rows written before centre_id existed carry only a child link.
        legacy = {"id": "inv-old", "number": "BA260001", "child_id": CHILD_ID,
                  "total_amount": "200", "due_date": "2099-01-01"}
        self._wire(db, kids, centres, access, by_centre=[], by_child=[legacy])

        res = self.client.get(f"/api/v1/centres/{CENTRE_ID}/invoices/")

        self.assertIn("BA260001", [i.get("number") for i in res.data["invoices"]])

    def test_debtors_chases_a_childless_invoice(self, db, kids, centres, access):
        overdue = {"id": "inv-walkin", "number": "BA260010", "centre_id": CENTRE_ID,
                   "child_id": None, "student_name": "Walk-in",
                   "total_amount": "5000", "due_date": "2020-01-01"}
        self._wire(db, kids, centres, access, by_centre=[overdue])

        res = self.client.get(f"/api/v1/centres/{CENTRE_ID}/invoices/debtors/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(float(res.data["total_outstanding"]), 5000.0)
        self.assertEqual([d["invoice_number"] for d in res.data["debtors"]], ["BA260010"])
