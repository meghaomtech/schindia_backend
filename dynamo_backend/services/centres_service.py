"""DynamoDB service for Centre and Room operations."""

import uuid
from ..service import DynamoDBService
from ..tables import CENTRES_TABLE, ROOMS_TABLE


class CentresDynamoService:
    def __init__(self):
        self.centres = DynamoDBService(CENTRES_TABLE)
        self.rooms = DynamoDBService(ROOMS_TABLE)
        # Local import avoids a module-load cycle — roles_service has no
        # dependency back on centres_service, so this is safe at import time
        # too, but keeping it lazy mirrors how the rest of this module avoids
        # reaching into other services' internals.
        from .roles_service import RolesDynamoService
        self.roles = RolesDynamoService()

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
        centre = self._enrich(centre)
        centre['sub_centre_count'] = 0
        return centre

    def get_centre(self, centre_id):
        """Get centre with its rooms, manager, affiliates and hierarchy info."""
        centre = self.centres.get(str(centre_id))
        if not centre:
            return None
        centre['rooms'] = self.get_rooms(centre_id)
        centre = self._enrich(centre)
        centre['sub_centre_count'] = len(self.list_sub_centres(centre_id, enrich=False))
        return centre

    def list_centres(self):
        """List all centres with rooms, manager, affiliates and hierarchy info."""
        centres = self.centres.list_all()
        by_id = {c['id']: c for c in centres}
        sub_counts = {}
        for c in centres:
            parent_id = c.get('parent_centre_id')
            if parent_id:
                sub_counts[parent_id] = sub_counts.get(parent_id, 0) + 1

        for centre in centres:
            centre['rooms'] = self.get_rooms(centre['id'])
            self._enrich(centre, parents_by_id=by_id)
            centre['sub_centre_count'] = sub_counts.get(centre['id'], 0)
        return centres

    def list_sub_centres(self, parent_id, enrich=True):
        """List a centre's direct sub-centres."""
        subs = self.centres.query_by_field('parent_centre_id', str(parent_id))
        if enrich:
            return [self.get_centre(s['id']) for s in subs]
        return subs

    def update_centre(self, centre_id, updates):
        """Update centre fields."""
        updated = self.centres.update(str(centre_id), updates)
        if not updated:
            return None
        updated['rooms'] = self.get_rooms(centre_id)
        updated = self._enrich(updated)
        updated['sub_centre_count'] = len(self.list_sub_centres(centre_id, enrich=False))
        return updated

    def delete_centre(self, centre_id):
        """Delete centre and its rooms."""
        # Delete rooms first
        rooms = self.get_rooms(centre_id)
        for room in rooms:
            self.rooms.delete(room['id'])
        return self.centres.delete(str(centre_id))

    # Manager / Affiliate / Parent enrichment
    def _member_summary(self, member_id):
        """Resolve a Global Role member id to a display-friendly summary."""
        if not member_id:
            return None
        member = self.roles.get_member(member_id)
        if not member:
            return None
        return {'id': member['id'], 'name': member.get('name', ''), 'email': member.get('email', '')}

    def _enrich(self, centre, parents_by_id=None):
        """Attach manager/affiliates/parent_centre display objects to a centre dict."""
        manager_id = centre.get('manager_id')
        centre['manager'] = self._member_summary(manager_id)

        affiliate_ids = centre.get('affiliate_ids') or []
        centre['affiliates'] = [
            summary for summary in (self._member_summary(mid) for mid in affiliate_ids)
            if summary is not None
        ]

        parent_id = centre.get('parent_centre_id')
        if not parent_id:
            centre['parent_centre'] = None
        else:
            parent = parents_by_id.get(parent_id) if parents_by_id is not None else self.centres.get(str(parent_id))
            centre['parent_centre'] = (
                {'id': parent['id'], 'name': parent.get('name', ''), 'system_id': parent.get('system_id', '')}
                if parent else None
            )
        return centre

    def clear_manager(self, member_id):
        """Null out manager_id on any centre that had this Global Role member
        as its Centre Manager — cascade for when that member is removed from
        the global Centre Manager role."""
        centres = self.centres.query_by_field('manager_id', str(member_id))
        for c in centres:
            self.centres.update(c['id'], {'manager_id': None})
        return len(centres)

    def remove_affiliate_everywhere(self, member_id):
        """Strip this Global Role member from affiliate_ids on every centre —
        cascade for when that member is removed from the global Affiliate role."""
        member_id = str(member_id)
        centres = self.centres.list_all()
        count = 0
        for c in centres:
            ids = c.get('affiliate_ids') or []
            if member_id in ids:
                self.centres.update(c['id'], {'affiliate_ids': [i for i in ids if i != member_id]})
                count += 1
        return count

    # Room operations
    def get_rooms(self, centre_id):
        """Get all rooms for a centre."""
        return self.rooms.query_by_index('centre_id-index', 'centre_id', str(centre_id))

    def get_room(self, room_id):
        """Get a single room by id."""
        return self.rooms.get(str(room_id))

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
