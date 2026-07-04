"""DynamoDB service for Centre and Room operations."""

import uuid
from ..service import DynamoDBService
from ..tables import CENTRES_TABLE, ROOMS_TABLE


class CentresDynamoService:
    def __init__(self):
        self.centres = DynamoDBService(CENTRES_TABLE)
        self.rooms = DynamoDBService(ROOMS_TABLE)

    def _generate_system_id(self):
        """Generate next system ID (SC-001, SC-002, etc.)."""
        all_centres = self.centres.list_all()
        if not all_centres:
            return "SC-001"
        # Find max system_id
        existing_ids = [
            int(c['system_id'].split('-')[1])
            for c in all_centres
            if c.get('system_id', '').startswith('SC-')
        ]
        next_num = max(existing_ids) + 1 if existing_ids else 1
        return f"SC-{next_num:03d}"

    def create_centre(self, data):
        """Create a centre with optional rooms."""
        rooms_data = data.pop('rooms', [])
        data['id'] = str(uuid.uuid4())
        data['system_id'] = self._generate_system_id()

        centre = self.centres.create(data)

        # Create rooms
        created_rooms = []
        for room in rooms_data:
            room['id'] = str(uuid.uuid4())
            room['centre_id'] = centre['id']
            created_rooms.append(self.rooms.create(room))

        centre['rooms'] = created_rooms
        return centre

    def get_centre(self, centre_id):
        """Get centre with its rooms."""
        centre = self.centres.get(str(centre_id))
        if centre:
            centre['rooms'] = self.get_rooms(centre_id)
        return centre

    def list_centres(self):
        """List all centres with rooms."""
        centres = self.centres.list_all()
        for centre in centres:
            centre['rooms'] = self.get_rooms(centre['id'])
        return centres

    def update_centre(self, centre_id, updates):
        """Update centre fields."""
        return self.centres.update(str(centre_id), updates)

    def delete_centre(self, centre_id):
        """Delete centre and its rooms."""
        # Delete rooms first
        rooms = self.get_rooms(centre_id)
        for room in rooms:
            self.rooms.delete(room['id'])
        return self.centres.delete(str(centre_id))

    # Room operations
    def get_rooms(self, centre_id):
        """Get all rooms for a centre."""
        return self.rooms.query_by_index('centre_id-index', 'centre_id', str(centre_id))

    def create_room(self, centre_id, data):
        """Create a room in a centre."""
        data['id'] = str(uuid.uuid4())
        data['centre_id'] = str(centre_id)
        return self.rooms.create(data)

    def update_room(self, room_id, updates):
        """Update a room."""
        return self.rooms.update(str(room_id), updates)

    def delete_room(self, room_id):
        """Delete a room."""
        return self.rooms.delete(str(room_id))
