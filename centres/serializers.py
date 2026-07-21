import re
from datetime import date

from rest_framework import serializers


class RoomSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=50)

    def validate_name(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError('Room name is required.')
        if len(value) > 50:
            raise serializers.ValidationError('Room name must be 50 characters or less.')
        return value.strip()


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


class CentreCreateSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    system_id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    street_address = serializers.CharField(max_length=200)
    city = serializers.CharField(max_length=50)
    postcode = serializers.CharField(max_length=10)
    vat_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=15)
    email = serializers.EmailField()
    manager_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    max_capacity = serializers.IntegerField(required=False, default=500)
    rooms = RoomSerializer(many=True, required=False)
    closure_dates = serializers.JSONField(required=False, default=list)
    opening_times = serializers.JSONField(required=False, default=dict)
    bank_details = serializers.JSONField(required=False, allow_null=True)

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
        cleaned = value.strip()
        # Accept Indian PIN codes (6 digits) — primary format
        # Also accept existing UK-format postcodes for backward compatibility
        if not (re.match(r'^\d{6}$', cleaned) or re.match(r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$', cleaned, re.IGNORECASE)):
            raise serializers.ValidationError('Postcode must be a valid 6-digit PIN code.')
        return cleaned

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
            # Validate each entry through ClosureDateSerializer (enforces date format + future date)
            entry_serializer = ClosureDateSerializer(data=entry)
            entry_serializer.is_valid(raise_exception=True)

            entry_date = str(entry.get('date', ''))
            reason = entry.get('reason', '')
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
