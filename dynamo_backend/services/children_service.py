"""DynamoDB service for Child, Contact, and Enrolment operations."""

import uuid
from datetime import datetime
from ..service import DynamoDBService
from ..tables import CHILDREN_TABLE, CONTACTS_TABLE, ENROLMENTS_TABLE


def is_archived(child):
    """
    Whether a child has been archived.

    One reading of the flag, shared by the service and the API, because
    children stored before archiving existed carry no `archived` attribute at
    all and must read as active rather than as neither.
    """
    return bool((child or {}).get('archived'))


class ChildrenDynamoService:
    def __init__(self):
        self.children = DynamoDBService(CHILDREN_TABLE)
        self.contacts = DynamoDBService(CONTACTS_TABLE)
        self.enrolments = DynamoDBService(ENROLMENTS_TABLE)

    def _generate_system_id(self):
        """Generate next child system ID (CHD-001, CHD-002, etc.)."""
        all_children = self.children.list_all()
        if not all_children:
            return "CHD-001"
        existing_ids = [
            int(c['system_id'].split('-')[1])
            for c in all_children
            if c.get('system_id', '').startswith('CHD-')
        ]
        next_num = max(existing_ids) + 1 if existing_ids else 1
        return f"CHD-{next_num:03d}"

    # Child CRUD
    def create_child(self, data):
        """Create a child with optional contacts."""
        contacts_data = data.pop('contacts', [])
        data['id'] = str(uuid.uuid4())
        data['system_id'] = self._generate_system_id()

        child = self.children.create(data)

        # Create contacts
        created_contacts = []
        for contact in contacts_data:
            contact['id'] = str(uuid.uuid4())
            contact['child_id'] = child['id']
            created_contacts.append(self.contacts.create(contact))

        child['contacts'] = created_contacts
        return child

    def get_child(self, child_id):
        """Get child with contacts."""
        child = self.children.get(str(child_id))
        if child:
            child['contacts'] = self.list_contacts(child_id)
        return child

    def list_children(self, centre_id=None, archived=None):
        """
        List children, optionally filtered by centre.

        `archived` selects on the archive flag: False for the active roll,
        True for the archive, None (the default) for everything. None stays
        the default because callers that reach children on their way to
        something else — invoices, the timetable, reporting — need the whole
        set; an archived child's invoices do not stop existing.
        """
        if centre_id:
            children = self.children.query_by_index('centre_id-index', 'centre_id', str(centre_id))
        else:
            children = self.children.list_all()
        if archived is not None:
            children = [c for c in children if is_archived(c) is archived]
        for child in children:
            child['contacts'] = self.list_contacts(child['id'])
        return children

    def update_child(self, child_id, updates):
        return self.children.update(str(child_id), updates)

    def archive_child(self, child_id, archived_by=''):
        """
        Take a child off the active roll without losing anything.

        A soft flag, never a delete: contacts, enrolments, journey entries,
        notes and invoices all hang off this record, and a centre asked in two
        years what a family was billed still has to be able to answer.
        """
        # Remove from all slots to free up capacity
        enrolments = self.list_enrolments(child_id, include_cancelled=False)
        for e in enrolments:
            slot_id = e.get('slot_id') or e.get('slot')
            if slot_id:
                self._remove_child_from_slot(str(slot_id), str(child_id))

        return self.children.update(str(child_id), {
            'archived': True,
            'archived_at': datetime.utcnow().isoformat(),
            'archived_by': archived_by,
        })

    def unarchive_child(self, child_id):
        """Put an archived child back on the active roll."""
        # Restore them to the slots they have active enrolments for
        enrolments = self.list_enrolments(child_id, include_cancelled=False)
        for e in enrolments:
            slot_id = e.get('slot_id') or e.get('slot')
            if slot_id:
                self._add_child_to_slot(str(slot_id), str(child_id))

        return self.children.update(str(child_id), {
            'archived': False,
            'archived_at': None,
            'archived_by': None,
        })

    def delete_child(self, child_id):
        # Delete contacts first
        contacts = self.list_contacts(child_id)
        for c in contacts:
            self.contacts.delete(c['id'])
        return self.children.delete(str(child_id))

    # Contact CRUD
    def list_contacts(self, child_id):
        return self.contacts.query_by_index('child_id-index', 'child_id', str(child_id))

    def get_contact(self, contact_id):
        return self.contacts.get(str(contact_id))

    def create_contact(self, child_id, data):
        data['id'] = str(uuid.uuid4())
        data['child_id'] = str(child_id)
        return self.contacts.create(data)

    def update_contact(self, contact_id, updates):
        return self.contacts.update(str(contact_id), updates)

    def delete_contact(self, contact_id):
        return self.contacts.delete(str(contact_id))

    # Enrolment CRUD
    def list_enrolments(self, child_id, include_cancelled=False):
        """
        A child's enrolments.

        Cancelled ones are held back by default — they are history, not a
        current booking — but the activity feed asks for them, so a parent can
        see that a place ended rather than watching it silently vanish.
        """
        rows = self.enrolments.query_by_index('child_id-index', 'child_id', str(child_id))
        if include_cancelled:
            return rows
        return [r for r in rows if not r.get('cancelled_at')]

    def get_enrolment(self, enrolment_id):
        return self.enrolments.get(str(enrolment_id))

    def create_enrolment(self, data):
        item = dict(data)
        item['id'] = str(uuid.uuid4())
        enrolment = self.enrolments.create(item)

        # Sync slot's child_ids to maintain timetable capacity counts
        slot_id = item.get('slot_id') or item.get('slot')
        child_id = item.get('child_id') or item.get('child')
        if slot_id and child_id:
            self._add_child_to_slot(str(slot_id), str(child_id))

        return enrolment

    def update_enrolment(self, enrolment_id, updates):
        old_enrolment = self.get_enrolment(enrolment_id)
        updated = self.enrolments.update(str(enrolment_id), updates)

        if old_enrolment and updated:
            old_slot_id = old_enrolment.get('slot_id') or old_enrolment.get('slot')
            new_slot_id = updated.get('slot_id') or updated.get('slot')
            child_id = updated.get('child_id') or updated.get('child')

            if old_slot_id != new_slot_id and child_id:
                if old_slot_id:
                    self._remove_child_from_slot(str(old_slot_id), str(child_id))
                if new_slot_id:
                    self._add_child_to_slot(str(new_slot_id), str(child_id))

        return updated

    def delete_enrolment(self, enrolment_id):
        """
        Cancel an enrolment.

        Marked cancelled rather than erased. The child comes off the slot
        either way, so capacity frees up immediately — but a booking that
        simply disappears leaves nobody able to say a place was ever held,
        which is what "Removed from Tiger" in a child's activity needs.

        `cancelled_at` is its own field rather than reusing end_date: an
        enrolment reaching its planned end is not a cancellation, and
        conflating them would report every completed term as a removal.
        """
        enrolment = self.get_enrolment(enrolment_id)
        if not enrolment:
            return None

        slot_id = enrolment.get('slot_id') or enrolment.get('slot')
        child_id = enrolment.get('child_id') or enrolment.get('child')
        if slot_id and child_id:
            self._remove_child_from_slot(str(slot_id), str(child_id))

        return self.enrolments.update(
            str(enrolment_id), {'cancelled_at': datetime.utcnow().isoformat()}
        )

    def _add_child_to_slot(self, slot_id, child_id):
        """Add child_id to the slot's child_ids list in sessions table."""
        from .sessions_service import SessionsDynamoService
        sessions_svc = SessionsDynamoService()
        slot = sessions_svc.get_slot(slot_id)
        if slot:
            child_ids = slot.get('child_ids', [])
            if child_id not in child_ids:
                child_ids.append(child_id)
                sessions_svc.update_slot(slot_id, {'child_ids': child_ids})

    def _remove_child_from_slot(self, slot_id, child_id):
        """Remove child_id from the slot's child_ids list."""
        from .sessions_service import SessionsDynamoService
        sessions_svc = SessionsDynamoService()
        slot = sessions_svc.get_slot(slot_id)
        if slot:
            child_ids = slot.get('child_ids', [])
            if child_id in child_ids:
                child_ids.remove(child_id)
                sessions_svc.update_slot(slot_id, {'child_ids': child_ids})
