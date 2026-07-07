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

    def get_name(self, obj):
        return obj.get_full_name()

    def get_permissions(self, obj):
        """Return all permissions grouped by centre for permission-based routing (Req 24)."""
        from roles.models import RoleMember
        memberships = RoleMember.objects.filter(user=obj).select_related(
            'role', 'role__centre'
        ).prefetch_related('role__permissions')

        result = {}
        for membership in memberships:
            centre_id = str(membership.role.centre.id)
            if centre_id not in result:
                result[centre_id] = {
                    'role': membership.role.name,
                    'data_scope': membership.role.data_scope,
                    'permissions': [],
                }
            for perm in membership.role.permissions.filter(visible=True):
                if perm.key not in result[centre_id]['permissions']:
                    result[centre_id]['permissions'].append(perm.key)
        return result

    def get_centres(self, obj):
        """Return list of centres the user has access to (Req 24.3)."""
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


class RegisterSerializer(serializers.Serializer):
    """
    For POST /api/auth/register/
    Creates user with status=approved and returns JWT immediately.
    """
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
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


class RequestAccessSerializer(serializers.Serializer):
    """
    For POST /api/auth/request-access/
    Creates user with status=pending. No token returned.
    """
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
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
