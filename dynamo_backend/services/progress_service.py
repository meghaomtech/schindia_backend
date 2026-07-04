"""DynamoDB service for Journey and Notes operations."""

import uuid
from ..service import DynamoDBService
from ..tables import JOURNEY_TABLE, NOTES_TABLE


class ProgressDynamoService:
    def __init__(self):
        self.journey = DynamoDBService(JOURNEY_TABLE)
        self.notes = DynamoDBService(NOTES_TABLE)

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
