import logging
import secrets
import uuid

from django.core.files.storage import default_storage
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import auth_db, global_access_db, roles_db
from notifications.mailer import send_staff_invite_email
from .capabilities import has_global_capability
from .permissions_catalog import CAPABILITY_CATEGORIES
from .serializers import OnboardStaffSerializer, UpdateStaffProfileSerializer

logger = logging.getLogger(__name__)

# Staff-record fields that are only ever returned to callers holding the
# matching capability (see permissions_catalog 'Staff records'). Everything
# else on a person is visible to anyone who can see the directory.
IDENTITY_FIELDS = ('aadhaar_number', 'pan', 'documents')
BANK_FIELDS = ('bank_details',)

# Matches the wizard's stated limit ("PDF, image or Word document, up to
# 10 MB each"). Enforced here too — the client-side check is a convenience,
# not a control.
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/heic',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

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


def _visible_person(person, request):
    """
    Strip regulated fields the caller isn't entitled to see.

    Everyone may see their own full record — staff need access to the bank
    details they themselves submitted — which is why the self check short-
    circuits before the capability lookups.
    """
    caller_email = (getattr(request.user, 'email', '') or '').strip().lower()
    if (person.get('email') or '').strip().lower() == caller_email:
        return person

    visible = dict(person)
    if not has_global_capability(request.user, 'staff_identity_documents', request=request):
        for field in IDENTITY_FIELDS:
            visible.pop(field, None)
    if not has_global_capability(request.user, 'staff_bank_salary_details', request=request):
        for field in BANK_FIELDS:
            visible.pop(field, None)
    return visible


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
        'people': [_visible_person(p, request) for p in people],
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


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def person_detail(request, person_pk):
    """
    Read, correct or remove one staff record.

    GET returns the record through _visible_person, so identity and bank
    details reach only a caller entitled to them — the same rule the list
    endpoint applies.

    Writing requires the capability that creates staff, and identity and bank
    writes are re-checked separately: someone who cannot read those fields
    must not be able to overwrite them either, which is what onboarding
    already enforces on the way in. Deleting is gated the same way — it was
    previously open to any approved user.
    """
    person = global_access_db.get_person(str(person_pk))
    if not person:
        return Response({'detail': 'Person not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(_visible_person(person, request))

    if not has_global_capability(request.user, 'onboard_staff', request=request):
        return Response(
            {'detail': 'You do not have permission to manage staff records.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == 'DELETE':
        global_access_db.remove_person(str(person_pk))
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = UpdateStaffProfileSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    updates = dict(serializer.validated_data)

    if any(field in updates for field in IDENTITY_FIELDS) and not has_global_capability(
        request.user, 'staff_identity_documents', request=request
    ):
        return Response(
            {'detail': 'You do not have permission to set identity details.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if any(field in updates for field in BANK_FIELDS) and not has_global_capability(
        request.user, 'staff_bank_salary_details', request=request
    ):
        return Response(
            {'detail': 'You do not have permission to set bank details.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # A DateField validates to a date object, which will not serialise into
    # DynamoDB on its own.
    if updates.get('start_date'):
        updates['start_date'] = updates['start_date'].isoformat()

    updated = global_access_db.update_person(str(person_pk), updates)
    return Response(_visible_person(updated or {}, request))


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


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def onboard_staff(request):
    """
    The three-step Onboard staff wizard, submitted as one call.

    Creating a staff record and granting access are a single user intent —
    a person created without a role has nothing to sign in to — so this is
    one transaction-ish endpoint rather than three chatty ones.

    Writing identity or bank details requires the matching capability, so a
    caller who cannot *read* those fields cannot silently set them either.
    """
    if not has_global_capability(request.user, 'onboard_staff', request=request):
        return Response(
            {'detail': 'You do not have permission to onboard staff.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = OnboardStaffSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    profile = dict(serializer.validated_data['profile'])
    assignment = serializer.validated_data['assignment']

    if any(profile.get(f) for f in IDENTITY_FIELDS) and not has_global_capability(
        request.user, 'staff_identity_documents', request=request
    ):
        return Response(
            {'detail': 'You do not have permission to set identity details.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if profile.get('bank_details') and not has_global_capability(
        request.user, 'staff_bank_salary_details', request=request
    ):
        return Response(
            {'detail': 'You do not have permission to set bank details.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    # A role id is either a global role (organisation-wide, from the
    # global_access table) or a centre role (Teacher, Manager, ... defined
    # per centre in the roles app). Which table it lives in *is* its scope —
    # that's more reliable than inspecting `kind`, since custom global roles
    # like "Regional Head" carry no kind but are still org-wide.
    role_id = str(assignment['role_id'])
    role = global_access_db.get_role(role_id)
    
    centre_role = None
    if not role:
        # Check if they are mistakenly trying to onboard a centre-specific role
        centre_role = roles_db.get_role(role_id)
        if not centre_role:
            return Response({'role_id': ['Role not found.']}, status=status.HTTP_404_NOT_FOUND)

    centre_id = assignment.get('centre_id') or None
    if role and centre_id:
        return Response(
            {'centre_id': ['This role applies organisation-wide and takes no centre.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    email = profile['email'].strip().lower()
    
    existing_person = next(
        (p for p in global_access_db.list_people() if (p.get('email') or '').strip().lower() == email),
        None
    )

    name = profile.pop('name')
    profile.pop('email', None)
    member_type = profile.pop('member_type', 'person')
    if profile.get('start_date'):
        profile['start_date'] = profile['start_date'].isoformat()
    
    # Set the staff_scope based on the role assigned during onboarding
    profile['staff_scope'] = 'centre' if centre_role else 'global'

    # A directory entry alone can't sign in — login looks the email up in the
    # users table. Create the account here, approved, with a random password
    # nobody ever learns: the invite sends them through the reset flow to
    # choose their own, so no password is ever emailed.
    login_created = False
    login_user = auth_db.get_user_by_email(email)
    if not login_user:
        first_name, _, last_name = name.partition(' ')
        login_user = auth_db.create_user(
            email=email,
            password=secrets.token_urlsafe(32),
            first_name=first_name,
            last_name=last_name,
            role='staff',
            status='approved',
        )
        login_created = True

    if existing_person:
        person = global_access_db.update_person(existing_person['id'], profile)
        person['email'] = email
        person['name'] = name
        person['roles'] = existing_person.get('roles', [])
        
        if not centre_role:
            assignment_res = global_access_db.assign_role(
                person['id'], role_id,
                centre_id=centre_id, include_sub_centres=assignment.get('include_sub_centres', False)
            )
            if assignment_res is None:
                return Response(
                    {'email': ['This person is already assigned to this role.']},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            person['roles'].append({
                'assignment_id': assignment_res['id'],
                'role_id': str(role_id),
                'centre_id': centre_id,
                'include_sub_centres': assignment.get('include_sub_centres', False),
            })
    else:
        # The directory entry is created either way, so People lists everyone
        # regardless of which kind of role they hold.
        person = global_access_db.add_person(
            name, email, role_id,
            member_type=member_type,
            profile=profile,
            centre_id=centre_id,
            include_sub_centres=assignment.get('include_sub_centres', False),
            create_assignment=not centre_role,
        )

    # A centre role's membership lives in the roles app, which is what the
    # per-centre permission checks read — the directory row alone would grant
    # nothing at the centre.
    if centre_role:
        # Check per-centre uniqueness: user can't be in multiple roles at same centre
        if centre_id:
            all_roles = roles_db.list_roles(centre_id)
            user_login_id = str((login_user or {}).get('id'))
            for r in all_roles:
                for m in r.get('members', []):
                    if m.get('user_id') == user_login_id:
                        return Response(
                            {'email': ['This person already has a role at this centre.']},
                            status=status.HTTP_400_BAD_REQUEST
                        )

        # Must be the *login* user's id, not the directory person's — that's
        # what roles.access._resolve_user_access matches members against when
        # it works out what this user may do. Passing person['id'] silently
        # grants nothing.
        result = roles_db.add_member(
            role_id, (login_user or {}).get('id'), name=name, email=email
        )
        if result is None:
            return Response(
                {'email': ['This person is already in this role.']},
                status=status.HTTP_400_BAD_REQUEST
            )

    invite = {'sent': False, 'reason': 'not_requested'}
    if serializer.validated_data.get('send_invite', True):
        invite = send_staff_invite_email(person, role, None)

    return Response(
        {
            'person': _visible_person(person, request),
            'invite': invite,
            'login_created': login_created,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
@parser_classes([MultiPartParser])
def upload_staff_document(request):
    """
    Accept one supporting document and hand back the reference the wizard
    stores on the person. The file itself goes to S3 — never into DynamoDB
    and never back out through the API as bytes.
    """
    if not has_global_capability(request.user, 'staff_identity_documents', request=request):
        return Response(
            {'detail': 'You do not have permission to upload staff documents.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    upload = request.FILES.get('file')
    if not upload:
        return Response({'file': ['No file supplied.']}, status=status.HTTP_400_BAD_REQUEST)
    if upload.size > MAX_DOCUMENT_BYTES:
        return Response(
            {'file': [f'Files must be {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB or smaller.']},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if upload.content_type not in ALLOWED_DOCUMENT_TYPES:
        return Response(
            {'file': ['Upload a PDF, image or Word document.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    key = f"staff-documents/{uuid.uuid4()}/{upload.name}"
    try:
        saved_key = default_storage.save(key, upload)
    except Exception as e:
        logger.error(f"Staff document upload failed: {e}", exc_info=True)
        return Response(
            {'detail': 'Could not store the file. Try again.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({
        'name': request.data.get('name') or upload.name,
        'key': saved_key,
        'size': upload.size,
        'content_type': upload.content_type,
    }, status=status.HTTP_201_CREATED)
