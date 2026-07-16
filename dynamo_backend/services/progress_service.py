"""DynamoDB service for Journey, Notes, Attendance, and CourseProgress operations."""

import uuid
from datetime import timedelta, date
from ..service import DynamoDBService
from ..tables import JOURNEY_TABLE, NOTES_TABLE, ATTENDANCE_TABLE, COURSE_PROGRESS_TABLE


class ProgressDynamoService:
    def __init__(self):
        self.journey = DynamoDBService(JOURNEY_TABLE)
        self.notes = DynamoDBService(NOTES_TABLE)
        self.attendance = DynamoDBService(ATTENDANCE_TABLE)
        self.course_progress = DynamoDBService(COURSE_PROGRESS_TABLE)

    # Journey CRUD
    def list_journey(self, child_id):
        entries = self.journey.query_by_index('child_id-index', 'child_id', str(child_id))
        return sorted(entries, key=lambda x: x.get('date', ''), reverse=True)

    def create_journey_entry(self, child_id, data):
        item = dict(data)
        item['id'] = str(uuid.uuid4())
        item['child_id'] = str(child_id)
        return self.journey.create(item)

    def get_journey_entry(self, entry_id):
        return self.journey.get(str(entry_id))

    def update_journey_entry(self, entry_id, updates):
        return self.journey.update(str(entry_id), updates)

    def delete_journey_entry(self, entry_id):
        return self.journey.delete(str(entry_id))

    # Notes CRUD
    def list_notes(self, child_id):
        notes = self.notes.query_by_index('child_id-index', 'child_id', str(child_id))
        return sorted(notes, key=lambda x: x.get('date', ''), reverse=True)

    def create_note(self, child_id, data):
        item = dict(data)
        item['id'] = str(uuid.uuid4())
        item['child_id'] = str(child_id)
        return self.notes.create(item)

    def get_note(self, note_id):
        return self.notes.get(str(note_id))

    def update_note(self, note_id, updates):
        return self.notes.update(str(note_id), updates)

    def delete_note(self, note_id):
        return self.notes.delete(str(note_id))

    # Attendance CRUD
    def list_attendance(self, child_id, date_from=None, date_to=None):
        records = self.attendance.query_by_index('child_id-index', 'child_id', str(child_id))
        if date_from:
            records = [r for r in records if r.get('date', '') >= date_from]
        if date_to:
            records = [r for r in records if r.get('date', '') <= date_to]
        return sorted(records, key=lambda x: x.get('date', ''), reverse=True)

    def create_attendance(self, child_id, data):
        """Create attendance with duplicate guard (child + slot + date)."""
        item = dict(data)  # Don't mutate caller's dict
        item['id'] = str(uuid.uuid4())
        item['child_id'] = str(child_id)
        return self.attendance.create(item)

    def has_duplicate_attendance(self, child_id, slot_id, att_date):
        """Check if attendance already exists for child + slot + date."""
        records = self.list_attendance(str(child_id))
        for r in records:
            if r.get('slot_id') == str(slot_id) and r.get('date') == str(att_date):
                return True
        return False

    def get_attendance(self, attendance_id):
        return self.attendance.get(str(attendance_id))

    def update_attendance(self, attendance_id, updates):
        return self.attendance.update(str(attendance_id), updates)

    def delete_attendance(self, attendance_id):
        return self.attendance.delete(str(attendance_id))

    # Course Progress CRUD (child_id is the partition key — 1:1 relationship)
    def get_course_progress(self, child_id):
        return self.course_progress.get(str(child_id))

    def set_course_progress(self, child_id, data):
        """Upsert course progress — child_id is the PK, no race condition."""
        item = dict(data)
        item['child_id'] = str(child_id)
        item.pop('id', None)
        existing = self.get_course_progress(child_id)
        if existing:
            return self.course_progress.update(str(child_id), item)
        return self.course_progress.create(item)

    # Activity feed (combined)
    def get_activity_feed(self, child_id, limit=20):
        """Build activity timeline from attendance, journey, and notes."""
        activities = []

        # Attendance (already sorted by date desc from list_attendance)
        for att in self.list_attendance(child_id):
            activities.append({
                'type': 'attendance',
                'date': att.get('date', ''),
                'text': f"Attended {att.get('session_name', 'session')} with {att.get('teacher_name', 'teacher')}",
                'status': att.get('status', 'attended'),
                'created_at': att.get('created_at', ''),
            })

        # Journey entries (already sorted by date desc)
        for entry in self.list_journey(child_id):
            activities.append({
                'type': entry.get('type', 'observation').lower(),
                'date': entry.get('date', ''),
                'text': f"{entry.get('type', '')}: {entry.get('text', '')}",
                'staff_name': entry.get('staff_name', ''),
                'created_at': entry.get('created_at', ''),
            })

        # Notes (already sorted by date desc)
        for note in self.list_notes(child_id):
            activities.append({
                'type': 'note',
                'date': note.get('date', ''),
                'text': f"Note added {note.get('text', '')}",
                'staff_name': note.get('staff_name', ''),
                'created_at': note.get('created_at', ''),
            })

        # Sort by (date, created_at) descending for stable ordering
        activities.sort(
            key=lambda x: (x.get('date') or '', x.get('created_at') or ''),
            reverse=True
        )
        return activities[:limit]

    def get_child_stats(self, child_id):
        """Get stats for a child — single fetch, derive counts in memory."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_start_iso = week_start.isoformat()
        week_end_iso = week_end.isoformat()

        # Single fetch for all attendance
        all_records = self.list_attendance(child_id)
        attended = [r for r in all_records if r.get('status') == 'attended']
        total_sessions = len(attended)
        sessions_this_week = len([
            r for r in attended
            if week_start_iso <= (r.get('date') or '') <= week_end_iso
        ])

        journey_entries = len(self.list_journey(child_id))

        progress = self.get_course_progress(child_id)
        course_progress = (
            f"M{progress.get('current_month', 1)} W{progress.get('current_week', 1)}"
            if progress else 'M1 W1'
        )

        return {
            'sessions_this_week': sessions_this_week,
            'total_sessions': total_sessions,
            'journey_entries': journey_entries,
            'course_progress': course_progress,
        }
