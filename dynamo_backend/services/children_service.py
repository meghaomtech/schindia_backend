"""DynamoDB service for Child, Contact, and Enrolment operations."""

import uuid
from ..service import DynamoDBService
from ..tables import CHILDREN_TABLE, CONTACTS_TABLE, ENROLMENTS_TABLE


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

    def list_children(self, centre_id=None):
        """List children, optionally filtered by centre."""
        if centre_id:
            children = self.children.query_by_index('centre_id-index', 'centre_id', str(centre_id))
        else:
            children = self.children.list_all()
        for child in children:
            child['contacts'] = self.list_contacts(child['id'])
        return children

    def update_child(self, child_id, updates):
        return self.children.update(str(child_id), updates)

    def delete_child(self, child_id):
        # Delete contacts first
        contacts = self.list_contacts(child_id)
        for c in contacts:
            self.contacts.delete(c['id'])
        return self.children.delete(str(child_id))

    # Contact CRUD
    def list_contacts(self, child_id):
        return self.contacts.query_by_index('child_id-index', 'child_id', str(child_id))

    def create_contact(self, child_id, data):
        data['id'] = str(uuid.uuid4())
        data['child_id'] = str(child_id)
        return self.contacts.create(data)

    def update_contact(self, contact_id, updates):
        return self.contacts.update(str(contact_id), updates)

    def delete_contact(self, contact_id):
        return self.contacts.delete(str(contact_id))

    # Enrolment CRUD
    def list_enrolments(self, child_id):
        return self.enrolments.query_by_index('child_id-index', 'child_id', str(child_id))

    def create_enrolment(self, data):
        data['id'] = str(uuid.uuid4())
        return self.enrolments.create(data)

    def delete_enrolment(self, enrolment_id):
        return self.enrolments.delete(str(enrolment_id))
