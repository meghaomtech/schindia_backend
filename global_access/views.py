from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import global_access_db
from .permissions_catalog import CAPABILITY_CATEGORIES

# Built-in roles other screens depend on (selectable as a centre's manager /
# affiliate) — cannot be deleted or have their `kind` changed. Mirrors the
# frontend's isProtectedRole() in src/lib/globalAccess.ts.
PROTECTED_KINDS = {'super_admin', 'centre_manager', 'affiliate'}


class GlobalRoleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def list(self, request, *args, **kwargs):
        return Response(global_access_db.list_roles())

    def retrieve(self, request, *args, **kwargs):
        role = global_access_db.get_role(str(kwargs['pk']))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(role)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data.pop('kind', None)  # only assigned by the seed command, never via the API

        name = (data.get('name') or '').strip()
        if not name:
            return Response({'name': ['Role name is required.']}, status=status.HTTP_400_BAD_REQUEST)
        if len(name) > 50:
            return Response({'name': ['Role name must be 50 characters or less.']}, status=status.HTTP_400_BAD_REQUEST)

        existing = global_access_db.list_roles()
        if any(r.get('name', '').lower() == name.lower() for r in existing):
            return Response({'name': ['A role with that name already exists.']}, status=status.HTTP_400_BAD_REQUEST)

        data['name'] = name
        role = global_access_db.create_role(data)
        return Response(role, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        role = global_access_db.get_role(str(kwargs['pk']))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data.pop('kind', None)

        new_name = (data.get('name') or '').strip()
        if new_name:
            if len(new_name) > 50:
                return Response({'name': ['Role name must be 50 characters or less.']}, status=status.HTTP_400_BAD_REQUEST)
            existing = global_access_db.list_roles()
            if any(r['id'] != str(kwargs['pk']) and r.get('name', '').lower() == new_name.lower() for r in existing):
                return Response({'name': ['A role with that name already exists.']}, status=status.HTTP_400_BAD_REQUEST)
            data['name'] = new_name

        updated = global_access_db.update_role(str(kwargs['pk']), data)
        return Response(updated)

    def destroy(self, request, *args, **kwargs):
        role = global_access_db.get_role(str(kwargs['pk']))
        if not role:
            return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
        if role.get('kind') in PROTECTED_KINDS:
            return Response(
                {'detail': f"\"{role.get('name')}\" is a built-in role and cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        global_access_db.delete_role(str(kwargs['pk']))
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def global_people(request):
    """
    Every person holding a global role, flattened with role + permission
    counts — matches the frontend's People tab on the Global
    Roles & Permissions page.
    """
    people = global_access_db.list_people()
    roles = {r['id']: r for r in global_access_db.list_roles()}

    def granted_count(role_id):
        role = roles.get(role_id)
        if not role:
            return 0
        return sum(1 for p in role.get('permissions', []) if p.get('edit') or p.get('visible'))

    for person in people:
        for r in person.get('roles', []):
            r['permission_count'] = granted_count(r['role_id'])

    role_counts = {r['name']: r.get('member_count', 0) for r in roles.values()}

    return Response({
        'total': len(people),
        'role_counts': role_counts,
        'people': people,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def add_person(request):
    """Create a global person and assign them a role in one step."""
    name = (request.data.get('name') or '').strip()
    email = (request.data.get('email') or '').strip()
    role_id = request.data.get('role_id') or request.data.get('role')
    member_type = request.data.get('member_type', 'person')

    if not name:
        return Response({'name': ['Name is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not email:
        return Response({'email': ['Email is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not role_id:
        return Response({'role_id': ['A global role is required.']}, status=status.HTTP_400_BAD_REQUEST)

    role = global_access_db.get_role(str(role_id))
    if not role:
        return Response({'role_id': ['Role not found.']}, status=status.HTTP_404_NOT_FOUND)

    person = global_access_db.add_person(name, email, str(role_id), member_type=member_type)
    return Response(person, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def assign_role(request, person_pk):
    """Give an existing global person another role."""
    role_id = request.data.get('role_id') or request.data.get('role')
    if not role_id:
        return Response({'role_id': ['A global role is required.']}, status=status.HTTP_400_BAD_REQUEST)

    role = global_access_db.get_role(str(role_id))
    if not role:
        return Response({'role_id': ['Role not found.']}, status=status.HTTP_404_NOT_FOUND)

    assignment = global_access_db.assign_role(str(person_pk), str(role_id))
    if assignment is None:
        return Response({'detail': 'This person already holds that role.'}, status=status.HTTP_400_BAD_REQUEST)
    return Response(assignment, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def remove_assignment(request, assignment_pk):
    """Remove one role assignment from a person, without deleting the person record."""
    removed = global_access_db.remove_assignment(str(assignment_pk))
    if not removed:
        return Response({'detail': 'Assignment not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def remove_person(request, person_pk):
    """Remove a person from Global settings entirely — every role they hold."""
    global_access_db.remove_person(str(person_pk))
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def permissions_matrix(request):
    """Every global capability against every global role, grouped by category."""
    roles = global_access_db.list_roles()

    matrix = {}
    for category, entries in CAPABILITY_CATEGORIES.items():
        matrix[category] = []
        for key, label in entries:
            row = {'key': key, 'label': label, 'roles': {}}
            for role in roles:
                perm = next((p for p in role.get('permissions', []) if p.get('key') == key), None)
                row['roles'][role['id']] = {
                    'visible': perm.get('visible', False) if perm else False,
                    'edit': perm.get('edit', False) if perm else False,
                }
            matrix[category].append(row)

    roles_data = [{
        'id': r['id'],
        'name': r.get('name', ''),
        'kind': r.get('kind'),
        'member_count': r.get('member_count', 0),
    } for r in roles]

    return Response({'roles': roles_data, 'matrix': matrix})


@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def save_permissions_matrix(request):
    """
    Bulk update permissions for all global roles.
    Expected body: { "role_id": { "key": {"visible": bool, "edit": bool}, ... }, ... }
    """
    data = request.data
    skipped = []
    for role_id, perms in data.items():
        role = global_access_db.get_role(str(role_id))
        if not role:
            skipped.append(role_id)
            continue
        if role.get('kind') == 'super_admin':
            # Super Admin bypasses permission resolution entirely on the
            # frontend — its grants are fixed and not editable via the matrix.
            continue
        for key, flags in perms.items():
            global_access_db.update_permission(str(role_id), key, flags)

    resp = {'detail': 'Permissions saved successfully.'}
    if skipped:
        resp['skipped_role_ids'] = skipped
    return Response(resp)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def update_permission(request, role_pk, key):
    """Update a specific permission's flags for one global role."""
    role = global_access_db.get_role(str(role_pk))
    if not role:
        return Response({'detail': 'Role not found.'}, status=status.HTTP_404_NOT_FOUND)
    if role.get('kind') == 'super_admin':
        return Response({'detail': 'Super Admin permissions cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)

    result = global_access_db.update_permission(str(role_pk), key, request.data)
    return Response(result)
