"""DynamoDB service for Journey, Notes, Attendance, and CourseProgress operations."""

import uuid
from datetime import datetime, timedelta, date
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
        return self.journey.query_by_index('child_id-index', 'child_id', str(child_id))

    def create_journey_entry(self, child_id, data):
        data['id'] = str(uuid.uuid4())
        data['child_id'] = str(child_id)
        return self.journey.create(data)

    def get_journey_entry(self, entry_id):
        return self.journey.get(str(entry_id))

    def update_journey_entry(self, entry_id, updates):
        return self.journey.update(str(entry_id), updates)

    def delete_journey_entry(self, entry_id):
        return self.journey.delete(str(entry_id))

    # Notes CRUD
    def list_notes(self, child_id):
        return self.notes.query_by_index('child_id-index', 'child_id', str(child_id))

    def create_note(self, child_id, data):
        data['id'] = str(uuid.uuid4())
        data['child_id'] = str(child_id)
        return self.notes.create(data)

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
        data['id'] = str(uuid.uuid4())
        data['child_id'] = str(child_id)
        return self.attendance.create(data)

    def get_attendance(self, attendance_id):
        return self.attendance.get(str(attendance_id))

    def update_attendance(self, attendance_id, updates):
        return self.attendance.update(str(attendance_id), updates)

    def delete_attendance(self, attendance_id):
        return self.attendance.delete(str(attendance_id))

    def count_attendance(self, child_id, status='attended', date_from=None, date_to=None):
        """Count attendance records for a child."""
        records = self.list_attendance(child_id, date_from, date_to)
        return len([r for r in records if r.get('status') == status])

    # Course Progress CRUD
    def get_course_progress(self, child_id):
        results = self.course_progress.query_by_index('child_id-index', 'child_id', str(child_id))
        return results[0] if results else None

    def set_course_progress(self, child_id, data):
        existing = self.get_course_progress(child_id)
        if existing:
            return self.course_progress.update(existing['id'], data)
        data['id'] = str(uuid.uuid4())
        data['child_id'] = str(child_id)
        return self.course_progress.create(data)

    # Activity feed (combined)
    def get_activity_feed(self, child_id, limit=20):
        """Build activity timeline from attendance, journey, and notes."""
        activities = []

        # Attendance
        attendances = self.list_attendance(child_id)[:limit]
        for att in attendances:
            activities.append({
                'type': 'attendance',
                'date': att.get('date', ''),
                'text': f"Attended {att.get('session_name', 'session')} with {att.get('teacher_name', 'teacher')}",
                'status': att.get('status', 'attended'),
                'created_at': att.get('created_at', ''),
            })

        # Journey entries
        journey = self.list_journey(child_id)[:limit]
        for entry in journey:
            activities.append({
                'type': entry.get('type', 'observation').lower(),
                'date': entry.get('date', ''),
                'text': f"{entry.get('type', '')}: {entry.get('text', '')}",
                'staff_name': entry.get('staff_name', ''),
                'created_at': entry.get('created_at', ''),
            })

        # Notes
        notes = self.list_notes(child_id)[:limit]
        for note in notes:
            activities.append({
                'type': 'note',
                'date': note.get('date', ''),
                'text': f"Note added {note.get('text', '')}",
                'staff_name': note.get('staff_name', ''),
                'created_at': note.get('created_at', ''),
            })

        # Sort by date descending
        activities.sort(key=lambda x: x.get('date', ''), reverse=True)
        return activities[:limit]

    def get_child_stats(self, child_id):
        """Get stats for a child: sessions_this_week, total, journey, progress."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        sessions_this_week = self.count_attendance(
            child_id, 'attended',
            date_from=week_start.isoformat(),
            date_to=week_end.isoformat()
        )
        total_sessions = self.count_attendance(child_id, 'attended')
        journey_entries = len(self.list_journey(child_id))

        progress = self.get_course_progress(child_id)
        course_progress = f"M{progress.get('current_month', 1)} W{progress.get('current_week', 1)}" if progress else 'M1 W1'

        return {
            'sessions_this_week': sessions_this_week,
            'total_sessions': total_sessions,
            'journey_entries': journey_entries,
            'course_progress': course_progress,
        }
