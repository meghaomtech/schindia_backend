from rest_framework import serializers


class RolePermissionSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    key = serializers.CharField(max_length=100)
    edit = serializers.BooleanField(default=False)
    visible = serializers.BooleanField(default=False)


class RoleMemberSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    user = serializers.CharField(source='user_id')
    user_email = serializers.CharField(source='email', read_only=True)
    user_name = serializers.CharField(source='name', read_only=True)
    role_name = serializers.CharField(read_only=True, required=False)
    active_sessions = serializers.IntegerField(read_only=True, default=0)
    created_at = serializers.CharField(read_only=True)


class RoleSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    centre = serializers.CharField(source='centre_id', required=False)
    name = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True)
    data_scope = serializers.ChoiceField(choices=['all', 'own'], default='all')
    permissions = RolePermissionSerializer(many=True, required=False)
    members = RoleMemberSerializer(many=True, required=False)
    member_count = serializers.SerializerMethodField()
    created_at = serializers.CharField(read_only=True)

    def get_member_count(self, obj):
        return len(obj.get('members', []))


class RoleCreateSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    centre = serializers.CharField(source='centre_id', required=False)
    name = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True)
    data_scope = serializers.ChoiceField(choices=['all', 'own'], default='all')
    permissions = RolePermissionSerializer(many=True, required=False)

    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Role name is required.')
        return value.strip()
