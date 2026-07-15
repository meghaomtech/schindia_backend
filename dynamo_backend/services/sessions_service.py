"""DynamoDB service for Session and SessionSlot operations."""

import uuid
from datetime import timedelta, datetime
from ..service import DynamoDBService
from ..tables import SESSIONS_TABLE, SESSION_SLOTS_TABLE


DAY_MAP = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}


class SessionsDynamoService:
    def __init__(self):
        self.sessions = DynamoDBService(SESSIONS_TABLE)
        self.slots = DynamoDBService(SESSION_SLOTS_TABLE)

    # Session CRUD
    def create_session(self, centre_id, data):
        """Create a session for a centre."""
        data['id'] = str(uuid.uuid4())
        data['centre_id'] = str(centre_id)
        return self.sessions.create(data)

    def get_session(self, session_id):
        return self.sessions.get(str(session_id))

    def list_sessions(self, centre_id):
        return self.sessions.query_by_index('centre_id-index', 'centre_id', str(centre_id))

    def update_session(self, session_id, updates):
        return self.sessions.update(str(session_id), updates)

    def delete_session(self, session_id):
        return self.sessions.delete(str(session_id))

    # Slot CRUD
    def create_slot(self, centre_id, data):
        """Create a single slot."""
        data['id'] = str(uuid.uuid4())
        data['centre_id'] = str(centre_id)
        return self.slots.create(data)

    def get_slot(self, slot_id):
        return self.slots.get(str(slot_id))

    def list_slots(self, centre_id, week=None):
        """List slots for a centre, optionally filtered by week."""
        slots = self.slots.query_by_index('centre_id-index', 'centre_id', str(centre_id))
        if week:
            try:
                week_start = datetime.strptime(week, '%Y-%m-%d').date()
                week_end = week_start + timedelta(days=6)
                slots = [
                    s for s in slots
                    if s.get('start_date') and
                    week_start <= datetime.strptime(s['start_date'], '%Y-%m-%d').date() <= week_end
                ]
            except (ValueError, TypeError):
                pass
        return slots

    def list_slots_by_room(self, room_id):
        """List slots assigned to a specific room (uses room_id-index GSI)."""
        return self.slots.query_by_index('room_id-index', 'room_id', str(room_id))

    def update_slot(self, slot_id, updates):
        return self.slots.update(str(slot_id), updates)

    def delete_slot(self, slot_id):
        return self.slots.delete(str(slot_id))

    # Timetable generation
    def generate_slots(self, centre_id, data):
        """Generate recurring slots (up to 15) or one-off."""
        session = self.get_session(data['session_id'])
        if not session:
            return None, "Session not found."

        duration_minutes = session.get('duration_hours', 1) * 60 + session.get('duration_minutes', 30)
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        start_time = data['start_time']

        # Parse start_time to minutes
        time_parts = start_time.split(':')
        start_minutes = int(time_parts[0]) * 60 + int(time_parts[1])

        num_slots = 1 if data.get('booking_type') == 'one-off' else 15

        # Check for overlaps
        conflicts = []
        slot_dates = []
        for i in range(num_slots):
            slot_date = start_date + timedelta(weeks=i)
            slot_dates.append(slot_date)

            if self._has_overlap(centre_id, data['room_id'], slot_date, start_minutes, duration_minutes):
                conflicts.append(str(slot_date))

        if conflicts:
            return None, conflicts

        # Create slots
        created = []
        starting_month = data.get('starting_month', 1)
        starting_week = data.get('starting_week', 1)

        for slot_date in slot_dates:
            day = DAY_MAP[slot_date.weekday()]
            slot = {
                'id': str(uuid.uuid4()),
                'centre_id': str(centre_id),
                'room_id': data['room_id'],
                'session_id': data['session_id'],
                'day': day,
                'start_time': start_time,
                'booking_type': data.get('booking_type', 'recurring'),
                'start_date': str(slot_date),
                'starting_month': starting_month,
                'starting_week': starting_week,
                'teacher_ids': data.get('teacher_ids', []),
                'child_ids': data.get('child_ids', []),
                'notes': data.get('notes', ''),
            }
            created.append(self.slots.create(slot))

            starting_week += 1
            if starting_week > 4:
                starting_week = 1
                starting_month += 1

        return created, None

    def _has_overlap(self, centre_id, room_id, date, start_minutes, duration_minutes):
        """Check for time overlaps in the same room on the same date."""
        existing = self.slots.query_by_index('centre_id-index', 'centre_id', str(centre_id))
        proposed_end = start_minutes + duration_minutes

        for slot in existing:
            if slot.get('room_id') != room_id:
                continue
            if slot.get('start_date') != str(date):
                continue

            slot_time = slot.get('start_time', '00:00').split(':')
            slot_start = int(slot_time[0]) * 60 + int(slot_time[1])

            # Get session duration
            session = self.get_session(slot.get('session_id'))
            if session:
                slot_duration = session.get('duration_hours', 1) * 60 + session.get('duration_minutes', 30)
            else:
                slot_duration = 90  # default

            slot_end = slot_start + slot_duration

            if start_minutes < slot_end and proposed_end > slot_start:
                return True

        return False
