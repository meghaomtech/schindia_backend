from rest_framework import serializers
from .models import Role, RolePermission, RoleMember


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ['id', 'key', 'edit', 'visible']
        read_only_fields = ['id']


class RoleMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    role_name = serializers.CharField(source='role.name', read_only=True)
    active_sessions = serializers.SerializerMethodField()

    class Meta:
        model = RoleMember
        fields = ['id', 'user', 'user_email', 'user_name', 'role_name', 'active_sessions', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name()

    def get_active_sessions(self, obj):
        """Count timetable slots the person is currently assigned to as teacher."""
        from sessions_app.models import SessionSlot
        return SessionSlot.objects.filter(teachers=obj.user).count()


class RoleSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, read_only=True)
    members = RoleMemberSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'centre', 'name', 'description', 'data_scope',
            'permissions', 'members', 'member_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_member_count(self, obj):
        return obj.members.count()


class RoleCreateSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, required=False)

    class Meta:
        model = Role
        fields = ['id', 'centre', 'name', 'description', 'data_scope', 'permissions']
        read_only_fields = ['id']

    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Role name is required.')
        if len(value) > 50:
            raise serializers.ValidationError('Role name must be 50 characters or less.')
        return value.strip()

    def validate(self, data):
        """Check role name uniqueness within centre (case-insensitive)."""
        centre = data.get('centre') or (self.instance.centre if self.instance else None)
        name = data.get('name', '')

        if centre and name:
            existing = Role.objects.filter(
                centre=centre, name__iexact=name
            )
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    {'name': 'A role with this name already exists at this centre.'}
                )
        return data

    def create(self, validated_data):
        permissions_data = validated_data.pop('permissions', [])
        role = Role.objects.create(**validated_data)
        for perm_data in permissions_data:
            RolePermission.objects.create(role=role, **perm_data)
        return role

    def update(self, instance, validated_data):
        permissions_data = validated_data.pop('permissions', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if permissions_data is not None:
            instance.permissions.all().delete()
            for perm_data in permissions_data:
                RolePermission.objects.create(role=instance, **perm_data)

        return instance


class PermissionsMatrixSerializer(serializers.Serializer):
    """Serializer for bulk updating all permissions for a role."""
    permissions = RolePermissionSerializer(many=True)
