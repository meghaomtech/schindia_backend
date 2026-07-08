import re
from datetime import date

from rest_framework import serializers
from .models import Centre, Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name']
        read_only_fields = ['id']

    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Room name is required.')
        if len(value) > 50:
            raise serializers.ValidationError('Room name must be 50 characters or less.')
        return value.strip()


class CentreListSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)
    rooms_count = serializers.SerializerMethodField()
    closure_days_count = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()

    class Meta:
        model = Centre
        fields = [
            'id', 'system_id', 'name', 'street_address', 'city', 'postcode',
            'vat_number', 'phone', 'email', 'manager_name', 'max_capacity',
            'rooms', 'rooms_count', 'closure_dates', 'closure_days_count',
            'opening_times', 'bank_details', 'initials', 'created_at',
        ]
        read_only_fields = ['id', 'system_id', 'created_at']

    def get_rooms_count(self, obj):
        return obj.rooms.count()

    def get_closure_days_count(self, obj):
        return len(obj.closure_dates) if obj.closure_dates else 0

    def get_initials(self, obj):
        """First letter of each word in centre name, max 2 characters."""
        words = obj.name.split()
        return ''.join(w[0].upper() for w in words[:2])


class ClosureDateSerializer(serializers.Serializer):
    """Validates individual closure date entries."""
    date = serializers.DateField()
    reason = serializers.CharField(max_length=200)

    def validate_date(self, value):
        if value <= date.today():
            raise serializers.ValidationError(
                'Closure date must be a future date.'
            )
        return value


class BankDetailsSerializer(serializers.Serializer):
    """Validates bank details per Req 18."""
    account_holder_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=18, required=False, allow_blank=True)
    sort_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    ifsc_code = serializers.CharField(max_length=11, required=False, allow_blank=True)
    upi_id = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_account_number(self, value):
        if value and not re.match(r'^\d{8,18}$', value):
            raise serializers.ValidationError('Account number must be 8-18 digits.')
        return value

    def validate_sort_code(self, value):
        if value and not re.match(r'^\d{2}-\d{2}-\d{2}$', value):
            raise serializers.ValidationError('Sort code must be in format XX-XX-XX.')
        return value

    def validate_ifsc_code(self, value):
        if value and not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', value):
            raise serializers.ValidationError(
                'IFSC code must be 11 alphanumeric characters in format XXXX0XXXXXX.'
            )
        return value

    def validate_upi_id(self, value):
        if value and '@' not in value:
            raise serializers.ValidationError(
                'UPI ID must be in format identifier@provider.'
            )
        return value


class OpeningTimesSerializer(serializers.Serializer):
    """Validates opening times for a single day."""
    open = serializers.CharField(max_length=5)
    close = serializers.CharField(max_length=5)
    closed = serializers.BooleanField(default=False)

    def validate(self, data):
        if not data.get('closed', False):
            open_time = data.get('open', '')
            close_time = data.get('close', '')
            if open_time and close_time and close_time <= open_time:
                raise serializers.ValidationError(
                    'Closing time must be after opening time.'
                )
        return data


class CentreCreateSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, required=False)

    class Meta:
        model = Centre
        fields = [
            'id', 'system_id', 'name', 'street_address', 'city', 'postcode',
            'vat_number', 'phone', 'email', 'manager_name', 'max_capacity',
            'rooms', 'closure_dates', 'opening_times', 'bank_details',
        ]
        read_only_fields = ['id', 'system_id']

    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Centre name is required.')
        if len(value) > 100:
            raise serializers.ValidationError('Centre name must be 100 characters or less.')
        return value.strip()

    def validate_street_address(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Street address is required.')
        if len(value) > 200:
            raise serializers.ValidationError('Street address must be 200 characters or less.')
        return value.strip()

    def validate_city(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('City is required.')
        if len(value) > 50:
            raise serializers.ValidationError('City must be 50 characters or less.')
        return value.strip()

    def validate_postcode(self, value):
        if not value:
            raise serializers.ValidationError('Postcode is required.')
        if not re.match(r'^\d{6}$', value.strip()):
            raise serializers.ValidationError('Postcode must be a 6-digit numeric PIN code.')
        return value.strip()

    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError('Phone number is required.')
        digits = re.sub(r'[^0-9]', '', value)
        if len(digits) != 10:
            raise serializers.ValidationError('Phone number must be exactly 10 digits.')
        return value.strip()

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError('Email address is required.')
        return value

    def validate_closure_dates(self, value):
        if not value:
            return value
        seen_dates = set()
        for entry in value:
            if not isinstance(entry, dict):
                raise serializers.ValidationError('Each closure date must be an object with date and reason.')
            entry_date = entry.get('date')
            reason = entry.get('reason', '')
            if not entry_date:
                raise serializers.ValidationError('Each closure date must have a date.')
            if not reason:
                raise serializers.ValidationError('Each closure date must have a reason.')
            if len(reason) > 200:
                raise serializers.ValidationError('Closure reason must be 200 characters or less.')
            # Check for duplicate dates
            if entry_date in seen_dates:
                raise serializers.ValidationError(
                    f'A closure date already exists for {entry_date}.'
                )
            seen_dates.add(entry_date)
        return value

    def validate_opening_times(self, value):
        if not value:
            return value
        valid_days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
        for day, times in value.items():
            if day not in valid_days:
                continue
            if not isinstance(times, dict):
                continue
            if not times.get('closed', False):
                open_time = times.get('open', '')
                close_time = times.get('close', '')
                if open_time and close_time and close_time <= open_time:
                    raise serializers.ValidationError(
                        f'Closing time must be after opening time for {day}.'
                    )
        return value

    def validate_bank_details(self, value):
        if not value:
            # Req 2.9: Bank details mandatory on centre creation
            if not self.instance:  # Only on create
                raise serializers.ValidationError('Bank details are required when creating a centre.')
            return value
        serializer = BankDetailsSerializer(data=value)
        serializer.is_valid(raise_exception=True)
        return value

    def create(self, validated_data):
        rooms_data = validated_data.pop('rooms', [])
        centre = Centre.objects.create(**validated_data)
        for room_data in rooms_data:
            Room.objects.create(centre=centre, **room_data)

        # Create default "Admin" role with all permissions (Req 15.4)
        self._create_default_admin_role(centre)

        return centre

    def _create_default_admin_role(self, centre):
        """Create initial 'Admin' role with all permissions enabled."""
        from roles.models import Role, RolePermission, RoleMember

        admin_role = Role.objects.create(
            centre=centre,
            name='Admin',
            description='Full administrative access'
        )

        # Define all permission keys grouped by module
        permission_keys = [
            'centres.view', 'centres.edit',
            'sessions.view', 'sessions.edit',
            'timetable.view', 'timetable.edit',
            'children.view', 'children.edit',
            'invoices.view', 'invoices.edit',
            'people.view', 'people.manage',
            'roles.view', 'roles.manage',
        ]

        for key in permission_keys:
            RolePermission.objects.create(
                role=admin_role,
                key=key,
                edit=True,
                visible=True,
            )

        # Assign the request user to admin role if available
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            RoleMember.objects.create(role=admin_role, user=request.user)

        return admin_role

    def update(self, instance, validated_data):
        rooms_data = validated_data.pop('rooms', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If rooms are provided in update, sync them
        if rooms_data is not None:
            existing_ids = set(instance.rooms.values_list('id', flat=True))
            incoming_ids = set()

            for room_data in rooms_data:
                room_id = room_data.get('id')
                if room_id and room_id in existing_ids:
                    room = Room.objects.get(id=room_id)
                    room.name = room_data.get('name', room.name)
                    room.save()
                    incoming_ids.add(room_id)
                else:
                    new_room = Room.objects.create(centre=instance, **room_data)
                    incoming_ids.add(new_room.id)

            # Delete rooms not in the incoming list
            to_delete = existing_ids - incoming_ids
            Room.objects.filter(id__in=to_delete).delete()

        return instance
