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

    class Meta:
        model = RoleMember
        fields = ['id', 'user', 'user_email', 'user_name', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_user_name(self, obj):
        return obj.user.get_full_name()


class RoleSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, read_only=True)
    members = RoleMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = [
            'id', 'centre', 'name', 'description',
            'permissions', 'members', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class RoleCreateSerializer(serializers.ModelSerializer):
    permissions = RolePermissionSerializer(many=True, required=False)

    class Meta:
        model = Role
        fields = ['id', 'centre', 'name', 'description', 'permissions']
        read_only_fields = ['id']

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
