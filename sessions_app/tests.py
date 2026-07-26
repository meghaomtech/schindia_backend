"""
API tests for the sessions_app app (sessions, timetable slots, slot generation, timetable view).

Same approach as the other apps' suites: SimpleTestCase (settings.DATABASES is a dummy
backend), dynamo_backend.services mocked at the point they're imported, and
force_authenticate() instead of real JWTs.

Two views resolve their DynamoDB services via a *local* import inside the function body
rather than the module-level `sessions_app.views.sessions_db`/`centres_db`:
  - SessionViewSet.create() does `from .serializers import get_next_color` locally, and
    that function does its own `from dynamo_backend.services import sessions_db` — so
    color assignment is mocked by patching `sessions_app.serializers.get_next_color`
    directly rather than trying to intercept its internal sessions_db call.
  - `_timetable_dynamo()` (backing the `timetable` view) does
    `from dynamo_backend.services import centres_db as _centres_db` locally, which
    bypasses the module-level `sessions_app.views.centres_db` entirely — so timetable
    tests patch `dynamo_backend.services.centres_db` instead.
"""
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIClient

CENTRE_ID = "22222222-2222-2222-2222-222222222222"
SESSION_ID = "33333333-3333-3333-3333-333333333333"
SLOT_ID = "44444444-4444-4444-4444-444444444444"
ROOM_ID = "66666666-6666-6666-6666-666666666666"
USER_ID = "55555555-5555-5555-5555-555555555555"

DEFAULT_COLOR = {"bg": "#e0f2fe", "text": "#0369a1"}


class FakeUser:
    def __init__(self, user_id=USER_ID, status="approved", role="staff"):
        self.id = user_id
        self.pk = user_id
        self.is_authenticated = True
        self.is_anonymous = False
        self.status = status
        self.role = role


class SessionsAPITestCase(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = FakeUser()
        self.client.force_authenticate(user=self.user)


# =============================================================================
# Permissions
# =============================================================================

class SessionsPermissionsTests(SimpleTestCase):
    ENDPOINTS = [
        ("get", f"/api/v1/centres/{CENTRE_ID}/sessions/"),
        ("get", f"/api/v1/sessions/{SESSION_ID}/"),
        ("post", f"/api/v1/centres/{CENTRE_ID}/sessions/"),
        ("get", f"/api/v1/centres/{CENTRE_ID}/slots/"),
        ("get", f"/api/v1/centres/{CENTRE_ID}/timetable/"),
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
# SessionViewSet: list / retrieve
# =============================================================================

@patch('sessions_app.views.sessions_db')
class SessionListRetrieveTests(SessionsAPITestCase):
    def test_list_nested_under_centre(self, mock_sessions_db):
        mock_sessions_db.list_sessions.return_value = [{"id": SESSION_ID}]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/sessions/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_sessions_db.list_sessions.assert_called_once_with(CENTRE_ID)

    def test_list_standalone_without_centre_returns_empty(self, mock_sessions_db):
        resp = self.client.get('/api/v1/sessions/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])
        mock_sessions_db.list_sessions.assert_not_called()

    def test_list_standalone_with_centre_query_param(self, mock_sessions_db):
        mock_sessions_db.list_sessions.return_value = [{"id": SESSION_ID}]

        resp = self.client.get(f'/api/v1/sessions/?centre={CENTRE_ID}')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_sessions_db.list_sessions.assert_called_once_with(CENTRE_ID)

    def test_retrieve_not_found(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = None

        resp = self.client.get(f'/api/v1/sessions/{SESSION_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_found(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID}

        resp = self.client.get(f'/api/v1/sessions/{SESSION_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# =============================================================================
# SessionViewSet: create
# =============================================================================

@patch('sessions_app.serializers.get_next_color')
@patch('sessions_app.views.sessions_db')
class SessionCreateTests(SessionsAPITestCase):
    def test_create_without_centre_is_rejected(self, mock_sessions_db, mock_get_next_color):
        resp = self.client.post('/api/v1/sessions/', {"name": "Session A"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_sessions_db.create_session.assert_not_called()

    def test_create_duplicate_name_case_insensitive(self, mock_sessions_db, mock_get_next_color):
        mock_sessions_db.list_sessions.return_value = [{"name": "Session A"}]

        resp = self.client.post(f'/api/v1/centres/{CENTRE_ID}/sessions/', {"name": "session a"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", resp.data["name"][0])
        mock_sessions_db.create_session.assert_not_called()

    def test_create_duration_too_short(self, mock_sessions_db, mock_get_next_color):
        mock_sessions_db.list_sessions.return_value = []

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/sessions/',
            {"name": "Session A", "durationHours": 0, "durationMinutes": 15},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("at least 30 minutes", resp.data["duration_minutes"][0])

    def test_create_duration_too_long(self, mock_sessions_db, mock_get_next_color):
        mock_sessions_db.list_sessions.return_value = []

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/sessions/',
            {"name": "Session A", "durationHours": 9, "durationMinutes": 0},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("480 minutes", resp.data["duration_minutes"][0])

    def test_create_child_limit_out_of_range(self, mock_sessions_db, mock_get_next_color):
        mock_sessions_db.list_sessions.return_value = []

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/sessions/', {"name": "Session A", "childLimit": 0}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("between 1 and 50", resp.data["child_limit"][0])

    def test_create_age_from_must_be_less_than_age_to(self, mock_sessions_db, mock_get_next_color):
        mock_sessions_db.list_sessions.return_value = []

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/sessions/',
            {"name": "Session A", "ageFrom": 5, "ageTo": 2},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("age_from must be less than age_to", resp.data["age_from"][0])

    def test_create_success_assigns_color_and_strips_centre(self, mock_sessions_db, mock_get_next_color):
        mock_sessions_db.list_sessions.return_value = []
        mock_sessions_db.create_session.return_value = {"id": SESSION_ID, "name": "Session A"}
        mock_get_next_color.return_value = DEFAULT_COLOR

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/sessions/',
            {"name": "Session A", "centre": CENTRE_ID},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        sent_data = mock_sessions_db.create_session.call_args[0][1]
        self.assertEqual(sent_data["color_bg"], DEFAULT_COLOR["bg"])
        self.assertEqual(sent_data["color_text"], DEFAULT_COLOR["text"])
        self.assertNotIn("centre", sent_data)


# =============================================================================
# SessionViewSet: partial_update / destroy
# =============================================================================

@patch('sessions_app.views.sessions_db')
class SessionUpdateDestroyTests(SessionsAPITestCase):
    def test_update_not_found(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = None

        resp = self.client.patch(f'/api/v1/sessions/{SESSION_ID}/', {"name": "New"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_scope_mismatch_is_404(self, mock_sessions_db):
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "centre_id": other_centre}

        resp = self.client.patch(f'/api/v1/centres/{CENTRE_ID}/sessions/{SESSION_ID}/', {"name": "New"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_sessions_db.update_session.assert_not_called()

    def test_update_success(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "centre_id": CENTRE_ID}
        mock_sessions_db.update_session.return_value = {"id": SESSION_ID, "name": "New"}

        resp = self.client.patch(f'/api/v1/sessions/{SESSION_ID}/', {"name": "New"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_sessions_db.update_session.assert_called_once_with(SESSION_ID, {"name": "New"})

    def test_destroy_not_found(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = None

        resp = self.client.delete(f'/api/v1/sessions/{SESSION_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_scope_mismatch_is_404(self, mock_sessions_db):
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "centre_id": other_centre}

        resp = self.client.delete(f'/api/v1/centres/{CENTRE_ID}/sessions/{SESSION_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_sessions_db.delete_session.assert_not_called()

    def test_destroy_blocked_by_dependent_slots(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "centre_id": CENTRE_ID}
        mock_sessions_db.list_slots.return_value = [{"session_id": SESSION_ID}]

        resp = self.client.delete(f'/api/v1/sessions/{SESSION_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_sessions_db.delete_session.assert_not_called()

    def test_destroy_success(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "centre_id": CENTRE_ID}
        mock_sessions_db.list_slots.return_value = [{"session_id": "other-session"}]

        resp = self.client.delete(f'/api/v1/sessions/{SESSION_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_sessions_db.delete_session.assert_called_once_with(SESSION_ID)


# =============================================================================
# SessionSlotViewSet: list / retrieve
# =============================================================================

@patch('sessions_app.views.sessions_db')
class SlotListRetrieveTests(SessionsAPITestCase):
    def test_list_nested_under_centre_with_week(self, mock_sessions_db):
        mock_sessions_db.list_slots.return_value = [{"id": SLOT_ID}]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/slots/?week=2026-01-05')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_sessions_db.list_slots.assert_called_once_with(CENTRE_ID, "2026-01-05")

    def test_list_standalone_without_centre_returns_empty(self, mock_sessions_db):
        resp = self.client.get('/api/v1/slots/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])
        mock_sessions_db.list_slots.assert_not_called()

    def test_list_standalone_with_centre_query_param(self, mock_sessions_db):
        mock_sessions_db.list_slots.return_value = [{"id": SLOT_ID}]

        resp = self.client.get(f'/api/v1/slots/?centre={CENTRE_ID}')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_sessions_db.list_slots.assert_called_once_with(CENTRE_ID, None)

    def test_retrieve_not_found(self, mock_sessions_db):
        mock_sessions_db.get_slot.return_value = None

        resp = self.client.get(f'/api/v1/slots/{SLOT_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_found(self, mock_sessions_db):
        mock_sessions_db.get_slot.return_value = {"id": SLOT_ID}

        resp = self.client.get(f'/api/v1/slots/{SLOT_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# =============================================================================
# SessionSlotViewSet: create
# =============================================================================

@patch('sessions_app.views.sessions_db')
class SlotCreateTests(SessionsAPITestCase):
    def test_create_without_centre_is_rejected(self, mock_sessions_db):
        resp = self.client.post('/api/v1/slots/', {"sessionId": SESSION_ID}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_sessions_db.create_slot.assert_not_called()

    def test_create_session_not_found(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = None

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/', {"sessionId": SESSION_ID}, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_sessions_db.create_slot.assert_not_called()

    def test_create_conflict_detected(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "duration_hours": 1, "duration_minutes": 0}
        mock_sessions_db._has_overlap.return_value = True

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/',
            {
                "sessionId": SESSION_ID, "roomId": ROOM_ID,
                "startTime": "09:00", "startDate": "2026-01-05", "day": "mon", "bookingType": "one-off",
            },
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        mock_sessions_db.create_slot.assert_not_called()

    def test_create_success_without_room_or_date_skips_conflict_check(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "duration_hours": 1, "duration_minutes": 0}
        mock_sessions_db.create_slot.return_value = {"id": SLOT_ID}

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/',
            {"sessionId": SESSION_ID, "day": "mon", "bookingType": "one-off", "startDate": "2026-01-05"},
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_sessions_db._has_overlap.assert_not_called()

    def test_create_success_with_room_and_date(self, mock_sessions_db):
        mock_sessions_db.get_session.return_value = {"id": SESSION_ID, "duration_hours": 1, "duration_minutes": 0}
        mock_sessions_db._has_overlap.return_value = False
        mock_sessions_db.create_slot.return_value = {"id": SLOT_ID}

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/',
            {
                "sessionId": SESSION_ID, "roomId": ROOM_ID,
                "startTime": "09:00", "startDate": "2026-01-05", "day": "mon", "bookingType": "one-off",
            },
            format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_sessions_db.create_slot.assert_called_once()


# =============================================================================
# SessionSlotViewSet: partial_update / destroy
# =============================================================================

@patch('sessions_app.views.sessions_db')
class SlotUpdateDestroyTests(SessionsAPITestCase):
    def test_update_not_found(self, mock_sessions_db):
        mock_sessions_db.get_slot.return_value = None

        resp = self.client.patch(f'/api/v1/slots/{SLOT_ID}/', {"notes": "x"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_scope_mismatch_is_404(self, mock_sessions_db):
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_sessions_db.get_slot.return_value = {"id": SLOT_ID, "centre_id": other_centre}

        resp = self.client.patch(f'/api/v1/centres/{CENTRE_ID}/slots/{SLOT_ID}/', {"notes": "x"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_sessions_db.update_slot.assert_not_called()

    def test_update_success(self, mock_sessions_db):
        mock_sessions_db.get_slot.return_value = {"id": SLOT_ID, "centre_id": CENTRE_ID}
        mock_sessions_db.update_slot.return_value = {"id": SLOT_ID, "notes": "x"}

        resp = self.client.patch(f'/api/v1/slots/{SLOT_ID}/', {"notes": "x"}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_sessions_db.update_slot.assert_called_once_with(SLOT_ID, {"notes": "x"})

    def test_destroy_not_found(self, mock_sessions_db):
        mock_sessions_db.get_slot.return_value = None

        resp = self.client.delete(f'/api/v1/slots/{SLOT_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_destroy_scope_mismatch_is_404(self, mock_sessions_db):
        other_centre = "77777777-7777-7777-7777-777777777777"
        mock_sessions_db.get_slot.return_value = {"id": SLOT_ID, "centre_id": other_centre}

        resp = self.client.delete(f'/api/v1/centres/{CENTRE_ID}/slots/{SLOT_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_sessions_db.delete_slot.assert_not_called()

    def test_destroy_success(self, mock_sessions_db):
        mock_sessions_db.get_slot.return_value = {"id": SLOT_ID, "centre_id": CENTRE_ID}

        resp = self.client.delete(f'/api/v1/slots/{SLOT_ID}/')

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_sessions_db.delete_slot.assert_called_once_with(SLOT_ID)


# =============================================================================
# generate_slots
# =============================================================================

@patch('sessions_app.views.centres_db')
@patch('sessions_app.views.sessions_db')
class GenerateSlotsTests(SessionsAPITestCase):
    VALID_PAYLOAD = {
        "sessionId": SESSION_ID,
        "roomId": ROOM_ID,
        "startTime": "09:00:00",
        "bookingType": "recurring",
        "startDate": "2026-01-05",
    }

    def test_missing_required_fields(self, mock_sessions_db, mock_centres_db):
        resp = self.client.post(f'/api/v1/centres/{CENTRE_ID}/slots/generate/', {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        mock_sessions_db.generate_slots.assert_not_called()

    def test_centre_not_found(self, mock_sessions_db, mock_centres_db):
        mock_centres_db.get_centre.return_value = None

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/generate/', self.VALID_PAYLOAD, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        mock_sessions_db.generate_slots.assert_not_called()

    def test_session_not_found(self, mock_sessions_db, mock_centres_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        mock_sessions_db.generate_slots.return_value = (None, "Session not found.")

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/generate/', self.VALID_PAYLOAD, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_conflicts_detected(self, mock_sessions_db, mock_centres_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        mock_sessions_db.generate_slots.return_value = (None, ["2026-01-05"])

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/generate/', self.VALID_PAYLOAD, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp.data["conflicts"], ["2026-01-05"])

    def test_success(self, mock_sessions_db, mock_centres_db):
        mock_centres_db.get_centre.return_value = {"id": CENTRE_ID}
        mock_sessions_db.generate_slots.return_value = ([{"id": SLOT_ID}], None)

        resp = self.client.post(
            f'/api/v1/centres/{CENTRE_ID}/slots/generate/', self.VALID_PAYLOAD, format='json'
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data, [{"id": SLOT_ID}])


# =============================================================================
# timetable
# =============================================================================

@patch('sessions_app.views.sessions_db')
@patch('dynamo_backend.services.centres_db')
class TimetableTests(SessionsAPITestCase):
    def test_invalid_week_format(self, mock_centres_db, mock_sessions_db):
        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/timetable/?week=not-a-date')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_centre_not_found(self, mock_centres_db, mock_sessions_db):
        mock_centres_db.get_centre.return_value = None

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/timetable/')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_timetable_grouped_by_day(self, mock_centres_db, mock_sessions_db):
        mock_centres_db.get_centre.return_value = {
            "id": CENTRE_ID, "name": "Centre A", "rooms": [{"id": ROOM_ID, "name": "Sunflower"}],
            "opening_times": {}, "closure_dates": [],
        }
        mock_sessions_db.list_slots.return_value = [{
            "id": SLOT_ID, "room_id": ROOM_ID, "session_id": SESSION_ID,
            "start_date": "2026-01-05", "start_time": "09:00", "booking_type": "one-off",
            "child_ids": ["child-1"],
        }]
        mock_sessions_db.list_sessions.return_value = [{
            "id": SESSION_ID, "name": "Session A", "duration_hours": 1, "duration_minutes": 0,
            "child_limit": 12, "color_bg": "#e0f2fe", "color_text": "#0369a1",
        }]

        resp = self.client.get(f'/api/v1/centres/{CENTRE_ID}/timetable/?week=2026-01-05')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["week_start"], "2026-01-05")
        # 2026-01-05 is a Monday
        self.assertEqual(len(resp.data["timetable"]["mon"]), 1)
        entry = resp.data["timetable"]["mon"][0]
        self.assertEqual(entry["session_name"], "Session A")
        self.assertEqual(entry["room_name"], "Sunflower")
        self.assertEqual(entry["children_enrolled"], 1)

    def test_filters_by_room(self, mock_centres_db, mock_sessions_db):
        mock_centres_db.get_centre.return_value = {
            "id": CENTRE_ID, "name": "Centre A", "rooms": [], "opening_times": {}, "closure_dates": [],
        }
        mock_sessions_db.list_slots.return_value = [{
            "id": SLOT_ID, "room_id": "other-room", "session_id": SESSION_ID,
            "start_date": "2026-01-05", "start_time": "09:00", "booking_type": "one-off", "child_ids": [],
        }]
        mock_sessions_db.list_sessions.return_value = [{
            "id": SESSION_ID, "name": "Session A", "duration_hours": 1, "duration_minutes": 0,
        }]

        resp = self.client.get(
            f'/api/v1/centres/{CENTRE_ID}/timetable/?week=2026-01-05&filter_type=room&filter_id={ROOM_ID}'
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(sum(len(v) for v in resp.data["timetable"].values()), 0)
