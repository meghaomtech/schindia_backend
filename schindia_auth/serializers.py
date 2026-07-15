from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import RootAccessRequest

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    centres = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'status', 'permissions', 'centres', 'requested_at']
        read_only_fields = ['id', 'role', 'status', 'requested_at']

    def to_representation(self, instance):
        """Handle both Django User model and DynamoUser objects."""
        from schindia_auth.authentication import DynamoUser
        if isinstance(instance, DynamoUser):
            return {
                'id': instance.id,
                'name': instance.get_full_name(),
                'email': instance.email,
                'role': instance.role,
                'status': instance.status,
                'permissions': self.get_permissions(instance),
                'centres': self.get_centres(instance),
                'requested_at': instance.requested_at,
            }
        return super().to_representation(instance)

    def get_name(self, obj):
        return obj.get_full_name()

    def get_permissions(self, obj):
        """Return all permissions grouped by centre for permission-based routing (Req 24)."""
        from dynamo_backend.router import use_dynamo
        if use_dynamo():
            return self._get_permissions_dynamo(obj)

        from roles.models import RoleMember
        memberships = RoleMember.objects.filter(user=obj).select_related(
            'role', 'role__centre'
        ).prefetch_related('role__permissions')

        result = {}
        for membership in memberships:
            centre_id = str(membership.role.centre.id)
            if centre_id not in result:
                result[centre_id] = {
                    'roles': [],
                    'data_scope': membership.role.data_scope,
                    'permissions': [],
                }
            # Track all roles at this centre
            if membership.role.name not in [r for r in result[centre_id]['roles']]:
                result[centre_id]['roles'].append(membership.role.name)
            # Merge data_scope: most-permissive wins
            if membership.role.data_scope == 'all':
                result[centre_id]['data_scope'] = 'all'
            # Use Python filtering to leverage prefetch cache
            for perm in membership.role.permissions.all():
                if perm.visible and perm.key not in result[centre_id]['permissions']:
                    result[centre_id]['permissions'].append(perm.key)
        return result

    def _get_permissions_dynamo(self, obj):
        """Fetch permissions from DynamoDB for the user."""
        from dynamo_backend.services import roles_db, centres_db
        user_id = str(obj.id) if hasattr(obj, 'id') else str(obj.get('id', ''))

        centres = centres_db.list_centres()
        result = {}
        for centre in centres:
            cid = centre['id']
            roles = roles_db.list_roles(cid)
            for role in roles:
                members = role.get('members', [])
                user_is_member = any(m.get('user_id') == user_id for m in members)
                if user_is_member:
                    if cid not in result:
                        result[cid] = {
                            'roles': [],
                            'data_scope': role.get('data_scope', 'own'),
                            'permissions': [],
                        }
                    result[cid]['roles'].append(role.get('name', ''))
                    if role.get('data_scope') == 'all':
                        result[cid]['data_scope'] = 'all'
                    for perm in role.get('permissions', []):
                        if perm.get('visible', True):
                            key = perm.get('key', '')
                            if key and key not in result[cid]['permissions']:
                                result[cid]['permissions'].append(key)
        return result

    def get_centres(self, obj):
        """Return list of centres the user has access to (Req 24.3)."""
        from dynamo_backend.router import use_dynamo
        if use_dynamo():
            return self._get_centres_dynamo(obj)

        from roles.models import RoleMember
        memberships = RoleMember.objects.filter(user=obj).select_related('role__centre')
        centres = []
        seen = set()
        for m in memberships:
            cid = str(m.role.centre.id)
            if cid not in seen:
                seen.add(cid)
                centres.append({
                    'id': cid,
                    'name': m.role.centre.name,
                    'system_id': m.role.centre.system_id,
                })
        return centres

    def _get_centres_dynamo(self, obj):
        """Fetch centres for user from DynamoDB."""
        from dynamo_backend.services import roles_db, centres_db
        user_id = str(obj.id) if hasattr(obj, 'id') else str(obj.get('id', ''))

        centres = centres_db.list_centres()
        result = []
        seen = set()
        for centre in centres:
            cid = centre['id']
            roles = roles_db.list_roles(cid)
            for role in roles:
                members = role.get('members', [])
                if any(m.get('user_id') == user_id for m in members):
                    if cid not in seen:
                        seen.add(cid)
                        result.append({
                            'id': cid,
                            'name': centre.get('name', ''),
                            'system_id': centre.get('system_id', ''),
                        })
                    break
        return result


class RequestAccessSerializer(serializers.Serializer):
    """
    For POST /api/auth/request-access/
    Creates user with status=pending. No token returned.
    """
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        value = value.strip().lower()
        from dynamo_backend.router import use_dynamo
        if use_dynamo():
            # Skip SQLite check — DynamoDB check happens in the view
            return value
        existing = User.objects.filter(email=value).first()
        if existing:
            status = getattr(existing, 'status', 'unknown')
            if status == 'pending':
                raise serializers.ValidationError("An access request with this email is already pending approval.")
            elif status == 'approved':
                raise serializers.ValidationError("An account with this email already exists. Please log in instead.")
            elif status == 'rejected':
                raise serializers.ValidationError("A previous request with this email was rejected. Please contact the administrator.")
            else:
                raise serializers.ValidationError("A user with this email already exists.")
        return value


class RequestRootAccessSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        value = value.strip().lower()
        from dynamo_backend.router import use_dynamo
        if use_dynamo():
            return value
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if RootAccessRequest.objects.filter(email=value, status='pending').exists():
            raise serializers.ValidationError("A root access request for this email is already pending.")
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class AccessRequestSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'status', 'requested_at']
        read_only_fields = ['id', 'name', 'email', 'role', 'requested_at']

    def get_name(self, obj):
        return obj.get_full_name()
