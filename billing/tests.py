"""
API tests for the billing app.

The project stores all billing data in DynamoDB (see dynamo_backend/services/billing_service.py)
and settings.DATABASES is a dummy backend, so these tests never touch a real database:
- Tests inherit from SimpleTestCase (not TestCase / APITestCase), which skips Django's
  per-test DB flush/transaction machinery entirely.
- dynamo_backend.services.billing_db / centres_db / children_db are mocked at the point
  they're imported into billing.views, so no AWS calls are made.
- Auth is bypassed with APIClient.force_authenticate() using a lightweight fake user object
  shaped like schindia_auth.authentication.DynamoUser, instead of minting real JWTs.
"""
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

CHILD_ID = "11111111-1111-1111-1111-111111111111"
CENTRE_ID = "22222222-2222-2222-2222-222222222222"
INVOICE_ID = "33333333-3333-3333-3333-333333333333"
PURCHASE_ID = "44444444-4444-4444-4444-444444444444"
USER_ID = "55555555-5555-5555-5555-555555555555"


class FakeUser:
    """Stand-in for schindia_auth.authentication.DynamoUser."""

    def __init__(self, user_id=USER_ID, status="approved", role="staff"):
        self.id = user_id
        self.pk = user_id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = status
        self.role = role


class BillingAPITestCase(SimpleTestCase):
    """Common client setup for an authenticated, approved user."""

    def setUp(self):
        self.client = APIClient()
        self.user = FakeUser()
        self.client.force_authenticate(user=self.user)


# =============================================================================
# Permissions (IsAuthenticated, IsApprovedUser) — representative across endpoints
# =============================================================================

class BillingPermissionsTests(SimpleTestCase):
    """All billing endpoints share permission_classes = [IsAuthenticated, IsApprovedUser]."""

    ENDPOINTS = [
        ("get", "/api/v1/invoices/"),
        ("get", f"/api/v1/invoices/{INVOICE_ID}/"),
        ("post", "/api/v1/invoices/"),
        ("get", "/api/v1/invoices/summary/"),
        ("get", "/api/v1/purchases/"),
        ("get", f"/api/v1/centres/{CENTRE_ID}/invoices/"),
        ("get", f"/api/v1/centres/{CENTRE_ID}/invoices/generate-data/"),
        ("get", f"/api/v1/centres/{CENTRE_ID}/invoices/payments/"),
    ]

    def test_unauthenticated_requests_are_rejected(self):
        client = APIClient()
        for method, url in self.ENDPOINTS:
            with self.subTest(method=method, url=url):
                resp = getattr(client, method)(url)
                self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unapproved_user_requests_are_forbidden(self):
        client = APIClient()
        client.force_authenticate(user=FakeUser(status="pending"))
        for method, url in self.ENDPOINTS:
            with self.subTest(method=method, url=url):
                resp = getattr(client, method)(url)
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# =============================================================================
# InvoiceViewSet: list / retrieve / create / partial_update / destroy
# =============================================================================

@patch('billing.views.billing_db')
class InvoiceViewSetTests(BillingAPITestCase):
    def test_list_invoices_for_current_user(self, mock_db):
        mock_db.list_invoices.return_value = [{"id": INVOICE_ID, "status": "Draft"}]

        resp = self.client.get('/api/v1/invoices/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [{"id": INVOICE_ID, "status": "Draft"}])
        mock_db.list_invoices.assert_called_once_with(user_id=USER_ID)

    def test_list_invoices_nested_under_child(self, mock_db):
        mock_db.list_invoices.return_value = [{"id": INVOICE_ID, "child_id": CHILD_ID}]

        resp = self.client.get(f'/api/v1/children/{CHILD_ID}/invoices/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_db.list_invoices.assert_called_once_with(child_id=CHILD_ID)

    def test_retrieve_invoice_found(self, mock_db):
        mock_db.get_invoice.return_value = {"id": INVOICE_ID, "status": "Draft"}

        resp = self.client.get(f'/api/v1/invoices/{INVOICE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], INVOICE_ID)
        mock_db.get_invoice.assert_called_once_with(INVOICE_ID)

    def test_retrieve_invoice_not_found(self, mock_db):
        mock_db.get_invoice.return_value = None

        resp = self.client.get(f'/api/v1/invoices/{INVOICE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(resp.data["detail"], "Invoice not found.")

    def test_create_invoice_injects_current_user_id(self, mock_db):
        mock_db.create_invoice.return_value = {"id": INVOICE_ID, "user_id": USER_ID}
        payload = {"totalAmount": 100, "dueDate": "2026-08-01", "items": [{"description": "Fee", "unitPrice": 100}]}

        resp = self.client.post('/api/v1/invoices/', payload, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        sent_data = mock_db.create_invoice.call_args[0][0]
        self.assertEqual(sent_data["user_id"], USER_ID)
        self.assertEqual(sent_data["total_amount"], 100)
        self.assertEqual(sent_data["items"], [{"description": "Fee", "unit_price": 100}])

    def test_create_invoice_nested_under_child(self, mock_db):
        mock_db.create_invoice.return_value = {"id": INVOICE_ID}

        resp = self.client.post(f'/api/v1/children/{CHILD_ID}/invoices/', {"totalAmount": 50}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        sent_data = mock_db.create_invoice.call_args[0][0]
        self.assertEqual(sent_data["user_id"], USER_ID)

    def test_partial_update_invoice(self, mock_db):
        mock_db.update_invoice.return_value = {"id": INVOICE_ID, "status": "Sent"}

        resp = self.client.patch(f'/api/v1/invoices/{INVOICE_ID}/', {"status": "Sent"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_db.update_invoice.assert_called_once_with(INVOICE_ID, {"status": "Sent"})

    def test_destroy_invoice(self, mock_db):
        resp = self.client.delete(f'/api/v1/invoices/{INVOICE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_db.delete_invoice.assert_called_once_with(INVOICE_ID)


# =============================================================================
# InvoiceViewSet custom actions: send / mark_paid / mark_overdue / resend_email
# =============================================================================

@patch('billing.views.billing_db')
class InvoiceSendActionTests(BillingAPITestCase):
    def test_send_invoice_not_found(self, mock_db):
        mock_db.get_invoice.return_value = None

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/send/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_send_already_paid_invoice_is_rejected(self, mock_db):
        mock_db.get_invoice.return_value = {"id": INVOICE_ID, "status": "Paid"}

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/send/')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["detail"], "Cannot send a paid invoice.")
        mock_db.update_invoice.assert_not_called()

    def test_send_invoice_marks_it_sent_with_timestamp(self, mock_db):
        mock_db.get_invoice.return_value = {"id": INVOICE_ID, "status": "Draft"}
        mock_db.update_invoice.return_value = {"id": INVOICE_ID, "status": "Sent"}

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/send/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        args, _ = mock_db.update_invoice.call_args
        self.assertEqual(args[0], INVOICE_ID)
        self.assertEqual(args[1]["status"], "Sent")
        self.assertIn("sent_at", args[1])


@patch('billing.views.billing_db')
class InvoiceMarkPaidActionTests(BillingAPITestCase):
    def test_mark_paid_not_found(self, mock_db):
        mock_db.get_invoice.return_value = None

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/mark_paid/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_paid_success(self, mock_db):
        mock_db.get_invoice.return_value = {"id": INVOICE_ID, "status": "Sent"}
        mock_db.update_invoice.return_value = {"id": INVOICE_ID, "status": "Paid"}

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/mark_paid/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "Paid")
        mock_db.update_invoice.assert_called_once_with(INVOICE_ID, {"status": "Paid"})


@patch('billing.views.billing_db')
class InvoiceMarkOverdueActionTests(BillingAPITestCase):
    def test_mark_overdue_not_found(self, mock_db):
        mock_db.get_invoice.return_value = None

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/mark_overdue/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_overdue_success(self, mock_db):
        mock_db.get_invoice.return_value = {"id": INVOICE_ID, "status": "Sent"}
        mock_db.update_invoice.return_value = {"id": INVOICE_ID, "status": "Overdue"}

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/mark_overdue/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "Overdue")
        mock_db.update_invoice.assert_called_once_with(INVOICE_ID, {"status": "Overdue"})


@patch('billing.notifications.send_mail')
@patch('billing.views.billing_db')
class InvoiceResendEmailActionTests(BillingAPITestCase):
    """resend_email calls billing.notifications.send_invoice_email, which calls django's send_mail."""

    def _invoice(self):
        return {
            "id": INVOICE_ID,
            "number": "INV-001",
            "child_id": CHILD_ID,
            "total_amount": 100,
            "due_date": "2026-08-01",
        }

    def _child(self, with_parent_email=True):
        contacts = (
            [{"invite_as": "Parent", "email": "parent@example.com", "name": "Pat Parent"}]
            if with_parent_email else []
        )
        return {
            "id": CHILD_ID,
            "first_name": "Kid",
            "last_name": "One",
            "centre_id": CENTRE_ID,
            "contacts": contacts,
        }

    def test_resend_email_invoice_not_found(self, mock_db, mock_send_mail):
        mock_db.get_invoice.return_value = None

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/resend_email/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_send_mail.assert_not_called()

    @patch('billing.notifications.children_db')
    @patch('billing.notifications.centres_db')
    def test_resend_email_no_parent_contacts(self, mock_centres_db, mock_children_db, mock_db, mock_send_mail):
        mock_db.get_invoice.return_value = self._invoice()
        mock_children_db.get_child.return_value = self._child(with_parent_email=False)
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID, "name": "Centre A"}

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/resend_email/')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["detail"], "No parent email associated with this child.")
        mock_db.add_sent_to.assert_not_called()

    @patch('billing.notifications.children_db')
    @patch('billing.notifications.centres_db')
    def test_resend_email_all_sends_fail(self, mock_centres_db, mock_children_db, mock_db, mock_send_mail):
        mock_db.get_invoice.return_value = self._invoice()
        mock_children_db.get_child.return_value = self._child()
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID, "name": "Centre A"}
        mock_send_mail.side_effect = Exception("SMTP down")

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/resend_email/')

        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(resp.data["detail"], "Failed to send invoice email.")
        self.assertIn("SMTP down", resp.data["errors"][0])
        mock_db.add_sent_to.assert_not_called()

    @patch('billing.notifications.children_db')
    @patch('billing.notifications.centres_db')
    def test_resend_email_success_records_sent_to(self, mock_centres_db, mock_children_db, mock_db, mock_send_mail):
        mock_db.get_invoice.return_value = self._invoice()
        mock_children_db.get_child.return_value = self._child()
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID, "name": "Centre A"}

        resp = self.client.post(f'/api/v1/invoices/{INVOICE_ID}/resend_email/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["detail"], "Invoice email sent.")
        mock_db.add_sent_to.assert_called_once_with(INVOICE_ID, 'email', 'parent@example.com')


# =============================================================================
# invoice_summary
# =============================================================================

@patch('billing.views.billing_db')
class InvoiceSummaryTests(BillingAPITestCase):
    def test_summary_with_no_invoices(self, mock_db):
        mock_db.list_invoices.return_value = []

        resp = self.client.get('/api/v1/invoices/summary/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {"total_invoices": 0, "overdue_count": 0, "by_status": {}})

    def test_summary_groups_counts_and_totals_by_status(self, mock_db):
        mock_db.list_invoices.return_value = [
            {"status": "Draft", "total_amount": "100", "due_date": "2020-01-01"},
            {"status": "Sent", "total_amount": "50", "due_date": "2099-01-01"},
            {"status": "Sent", "total_amount": "25", "due_date": "2020-01-01"},
            {"status": "Paid", "total_amount": "200"},
        ]

        resp = self.client.get('/api/v1/invoices/summary/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_invoices"], 4)
        self.assertEqual(resp.data["by_status"]["Draft"], {"count": 1, "total_amount": 100.0})
        self.assertEqual(resp.data["by_status"]["Sent"], {"count": 2, "total_amount": 75.0})
        self.assertEqual(resp.data["by_status"]["Paid"], {"count": 1, "total_amount": 200.0})
        # overdue_count: Draft/Sent invoices whose due_date is in the past
        self.assertEqual(resp.data["overdue_count"], 2)

    def test_summary_defaults_missing_status_to_draft(self, mock_db):
        mock_db.list_invoices.return_value = [{"total_amount": "10"}]

        resp = self.client.get('/api/v1/invoices/summary/')

        self.assertEqual(resp.data["by_status"]["Draft"], {"count": 1, "total_amount": 10.0})


# =============================================================================
# PurchaseViewSet
# =============================================================================

@patch('billing.views.billing_db')
class PurchaseViewSetTests(BillingAPITestCase):
    def test_list_without_child_returns_empty(self, mock_db):
        resp = self.client.get('/api/v1/purchases/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])
        mock_db.list_purchases.assert_not_called()

    def test_list_purchases_for_child(self, mock_db):
        mock_db.list_purchases.return_value = [{"id": PURCHASE_ID, "child_id": CHILD_ID}]

        resp = self.client.get(f'/api/v1/children/{CHILD_ID}/purchases/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_db.list_purchases.assert_called_once_with(CHILD_ID)

    def test_create_without_child_is_rejected(self, mock_db):
        resp = self.client.post('/api/v1/purchases/', {"name": "Uniform"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["detail"], "A child is required to create a purchase.")
        mock_db.create_purchase.assert_not_called()

    def test_create_purchase_for_child(self, mock_db):
        mock_db.create_purchase.return_value = {"id": PURCHASE_ID, "child_id": CHILD_ID, "name": "Uniform"}

        resp = self.client.post(f'/api/v1/children/{CHILD_ID}/purchases/', {"name": "Uniform"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_db.create_purchase.assert_called_once_with(CHILD_ID, {"name": "Uniform"})

    def test_partial_update_purchase_via_router_route(self, mock_db):
        # The nested children/<child_pk>/purchases/<pk>/ route is broken for every verb —
        # see PurchaseNestedDetailRouteBugTests below — so this exercises the (working)
        # router-generated /api/v1/purchases/<pk>/ route instead.
        mock_db.update_purchase.return_value = {"id": PURCHASE_ID, "name": "Updated"}

        resp = self.client.patch(f'/api/v1/purchases/{PURCHASE_ID}/', {"name": "Updated"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_db.update_purchase.assert_called_once_with(PURCHASE_ID, {"name": "Updated"})

    def test_destroy_purchase_via_router_route(self, mock_db):
        resp = self.client.delete(f'/api/v1/purchases/{PURCHASE_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_db.delete_purchase.assert_called_once_with(PURCHASE_ID)


@patch('billing.views.billing_db')
class PurchaseNestedDetailRouteBugTests(BillingAPITestCase):
    """
    Known bug: billing/urls.py registers

        children/<child_pk>/purchases/<pk>/ -> {'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy'}

    but PurchaseViewSet never defines retrieve(). DRF's ViewSetMixin.as_view() calls
    getattr(self, action) for *every* action in that mapping while setting up the view —
    not just the one matching the incoming HTTP method — so a plain getattr(self, 'retrieve')
    blows up with AttributeError before dispatch() even looks at the request method. As a
    result GET, PATCH, and DELETE on this nested URL are all broken (500), even though only
    GET/retrieve is actually missing.

    These tests pin down today's (buggy) behavior so a fix — implementing retrieve(), or
    dropping 'get' from the route — is a deliberate, visible change rather than a silent
    regression. Once fixed, replace assertRaises(AttributeError) with the expected status code.
    """

    def test_get_crashes(self, mock_db):
        with self.assertRaises(AttributeError):
            self.client.get(f'/api/v1/children/{CHILD_ID}/purchases/{PURCHASE_ID}/')

    def test_patch_crashes_even_though_partial_update_exists(self, mock_db):
        with self.assertRaises(AttributeError):
            self.client.patch(f'/api/v1/children/{CHILD_ID}/purchases/{PURCHASE_ID}/', {"name": "x"}, format='json')

    def test_delete_crashes_even_though_destroy_exists(self, mock_db):
        with self.assertRaises(AttributeError):
            self.client.delete(f'/api/v1/children/{CHILD_ID}/purchases/{PURCHASE_ID}/')


# =============================================================================
# centre_invoices
# =============================================================================

@patch('billing.views.children_db')
@patch('billing.views.centres_db')
@patch('billing.views.billing_db')
class CentreInvoicesTests(BillingAPITestCase):
    def test_centre_not_found(self, mock_billing_db, mock_centres_db, mock_children_db):
        mock_centres_db.get_centre.return_value = None

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def _setup_two_children_with_invoices(self, mock_centres_db, mock_children_db, mock_billing_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID, "name": "Centre A"}
        mock_children_db.list_children.return_value = [
            {"id": "child-a"}, {"id": "child-b"},
        ]
        invoices_by_child = {
            "child-a": [
                {"id": "inv-1", "status": "Sent", "total_amount": "100", "invoice_date": "2026-01-01",
                 "student_name": "Alice", "number": "INV-1"},
                {"id": "inv-2", "status": "Overdue", "total_amount": "50", "invoice_date": "2026-02-01",
                 "student_name": "Alice", "number": "INV-2"},
            ],
            "child-b": [
                {"id": "inv-3", "status": "Paid", "total_amount": "200", "invoice_date": "2026-03-01",
                 "student_name": "Bob", "number": "INV-3"},
            ],
        }
        mock_billing_db.list_invoices.side_effect = lambda child_id: invoices_by_child[child_id]

    def test_returns_summary_and_full_invoice_list(self, mock_billing_db, mock_centres_db, mock_children_db):
        self._setup_two_children_with_invoices(mock_centres_db, mock_children_db, mock_billing_db)

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["summary"]["total_invoices"], 3)
        self.assertEqual(resp.data["summary"]["total_outstanding"], 150.0)
        self.assertEqual(resp.data["summary"]["total_paid"], 200.0)
        self.assertEqual(resp.data["summary"]["overdue_count"], 1)
        self.assertEqual(len(resp.data["invoices"]), 3)

    def test_filter_by_status(self, mock_billing_db, mock_centres_db, mock_children_db):
        self._setup_two_children_with_invoices(mock_centres_db, mock_children_db, mock_billing_db)

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/?status=Paid')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["invoices"]), 1)
        self.assertEqual(resp.data["invoices"][0]["id"], "inv-3")
        # summary stays computed over all centre invoices, unaffected by the filter
        self.assertEqual(resp.data["summary"]["total_invoices"], 3)

    def test_filter_by_date_range(self, mock_billing_db, mock_centres_db, mock_children_db):
        self._setup_two_children_with_invoices(mock_centres_db, mock_children_db, mock_billing_db)

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/?date_from=2026-02-01&date_to=2026-02-28')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([i["id"] for i in resp.data["invoices"]], ["inv-2"])

    def test_filter_by_search_matches_name_or_number(self, mock_billing_db, mock_centres_db, mock_children_db):
        self._setup_two_children_with_invoices(mock_centres_db, mock_children_db, mock_billing_db)

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/?search=bob')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([i["id"] for i in resp.data["invoices"]], ["inv-3"])

    def test_status_filter_all_returns_everything(self, mock_billing_db, mock_centres_db, mock_children_db):
        self._setup_two_children_with_invoices(mock_centres_db, mock_children_db, mock_billing_db)

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/?status=All')

        self.assertEqual(len(resp.data["invoices"]), 3)


# =============================================================================
# invoice_generate_data
# =============================================================================

@patch('billing.views.children_db')
@patch('billing.views.centres_db')
class InvoiceGenerateDataTests(BillingAPITestCase):
    def test_centre_not_found(self, mock_centres_db, mock_children_db):
        mock_centres_db.get_centre.return_value = None

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/generate-data/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_centre_and_children_data(self, mock_centres_db, mock_children_db):
        mock_centres_db.get_centre.return_value = {
            "id": CENTRE_ID,
            "system_id": "C-001",
            "name": "Centre A",
            "city": "Mumbai",
            "street_address": "1 Main St",
            "postcode": "400001",
            "email": "centre@example.com",
            "phone": "123",
            "vat_number": "GST123",
            "bank_details": {
                "bank_name": "Bank A",
                "account_number": "acct-1",
                "ifsc_code": "IFSC1",
                "upi_id": "upi@id",
                "account_holder_name": "Centre A Holder",
            },
        }
        mock_children_db.list_children.return_value = [
            {
                "id": CHILD_ID,
                "first_name": "Kid",
                "middle_name": "",
                "last_name": "One",
                "session_name": "Morning",
                "date_of_birth": "2020-01-01",
                "contacts": [
                    {"invite_as": "Guardian", "name": "Gary Guardian", "email": "gary@example.com", "phone": "999"},
                    {"invite_as": "Emergency", "name": "Not Parent", "email": "x@example.com", "phone": "000"},
                ],
            }
        ]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/generate-data/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["centre"]["centre_code"], "C-001")
        self.assertEqual(resp.data["centre"]["gst_number"], "GST123")
        self.assertEqual(resp.data["centre"]["full_address"], "1 Main St, Mumbai, 400001")
        self.assertTrue(resp.data["bank_details_complete"])

        child_data = resp.data["children"][0]
        self.assertEqual(child_data["student_name"], "Kid One")
        # picks the Guardian contact, not the Emergency one
        self.assertEqual(child_data["parent_name"], "Gary Guardian")
        self.assertEqual(child_data["parent_email"], "gary@example.com")

    def test_bank_details_incomplete_when_fields_missing(self, mock_centres_db, mock_children_db):
        mock_centres_db.get_centre.return_value = {
            "id": CENTRE_ID, "bank_details": {"bank_name": "Bank A"},
        }
        mock_children_db.list_children.return_value = []

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/generate-data/')

        self.assertFalse(resp.data["bank_details_complete"])

    def test_child_without_parent_contact_has_blank_parent_fields(self, mock_centres_db, mock_children_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID, "bank_details": {}}
        mock_children_db.list_children.return_value = [
            {"id": CHILD_ID, "first_name": "Kid", "last_name": "One", "contacts": []}
        ]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/generate-data/')

        child_data = resp.data["children"][0]
        self.assertEqual(child_data["parent_name"], "")
        self.assertEqual(child_data["parent_email"], "")
        self.assertEqual(child_data["parent_phone"], "")


# =============================================================================
# centre_payments
# =============================================================================

@patch('billing.views.children_db')
@patch('billing.views.centres_db')
@patch('billing.views.billing_db')
class CentrePaymentsTests(BillingAPITestCase):
    def test_centre_not_found(self, mock_billing_db, mock_centres_db, mock_children_db):
        mock_centres_db.get_centre.return_value = None

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/payments/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_only_paid_invoices_are_returned_sorted_by_payment_date_desc(
        self, mock_billing_db, mock_centres_db, mock_children_db
    ):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        mock_children_db.list_children.return_value = [
            {"id": "child-a", "first_name": "Alice", "last_name": "A"},
            {"id": "child-b", "first_name": "Bob", "last_name": "B"},
        ]

        def list_invoices(child_id):
            return {
                "child-a": [
                    {"id": "inv-1", "status": "Paid", "number": "INV-1", "total_amount": "100",
                     "updated_at": "2026-01-05T10:00:00", "due_date": "2026-01-10"},
                    {"id": "inv-2", "status": "Draft", "number": "INV-2", "total_amount": "10",
                     "updated_at": "2026-01-01T10:00:00", "due_date": "2026-01-10"},
                ],
                "child-b": [
                    {"id": "inv-3", "status": "Paid", "number": "INV-3", "total_amount": "200",
                     "updated_at": "2026-02-01T10:00:00", "due_date": "2026-02-10"},
                ],
            }[child_id]

        mock_billing_db.list_invoices.side_effect = list_invoices

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/payments/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        payments = resp.data["payments"]
        self.assertEqual(len(payments), 2)
        self.assertEqual(payments[0]["invoice_id"], "inv-3")
        self.assertEqual(payments[0]["payment_date"], "2026-02-01")
        self.assertEqual(payments[1]["invoice_id"], "inv-1")

    def test_falls_back_to_child_name_when_invoice_has_no_student_name(
        self, mock_billing_db, mock_centres_db, mock_children_db
    ):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        mock_children_db.list_children.return_value = [
            {"id": "child-a", "first_name": "Alice", "last_name": "A"},
        ]
        mock_billing_db.list_invoices.return_value = [
            {"id": "inv-1", "status": "Paid", "number": "INV-1", "total_amount": "100",
             "updated_at": "2026-01-05T10:00:00", "due_date": "2026-01-10"},
        ]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/invoices/payments/')

        self.assertEqual(resp.data["payments"][0]["student_name"], "Alice A")
