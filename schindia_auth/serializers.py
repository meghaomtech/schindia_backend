from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password


class UserSerializer(serializers.Serializer):
    """Serializes a DynamoUser (request.user) into the API user shape."""

    def to_representation(self, instance):
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

    def get_permissions(self, obj):
        """Return all permissions grouped by centre for permission-based routing (Req 24)."""
        from dynamo_backend.services import roles_db, centres_db
        user_id = str(obj.id)

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
        from dynamo_backend.services import roles_db, centres_db
        user_id = str(obj.id)

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
        return value.strip().lower()


class RequestRootAccessSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=300)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        return value.strip().lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
