"""
Serializers for the staff onboarding wizard (Global settings → People).

Split into three, mirroring the three steps the UI walks through, so a
partial save from step 1 can be validated without demanding the role that
only step 2 collects.

The identity and bank blocks are regulated personal data. They are validated
here but only ever *returned* through global_access.views._visible_person,
which strips them unless the caller holds the matching capability.
"""
import re

from rest_framework import serializers


AADHAAR_RE = re.compile(r'^\d{12}$')
PAN_RE = re.compile(r'^[A-Z]{5}\d{4}[A-Z]$')
IFSC_RE = re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$')
ACCOUNT_RE = re.compile(r'^\d{9,18}$')
PHONE_RE = re.compile(r'^\d{10}$')


class StaffBankDetailsSerializer(serializers.Serializer):
    """Salary payment details. Optional at onboarding, addable later."""
    account_holder_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bank_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    account_number = serializers.CharField(max_length=18, required=False, allow_blank=True)
    ifsc_code = serializers.CharField(max_length=11, required=False, allow_blank=True)

    def validate_account_number(self, value):
        if value and not ACCOUNT_RE.match(value):
            raise serializers.ValidationError('Account number must be 9-18 digits.')
        return value

    def validate_ifsc_code(self, value):
        if value and not IFSC_RE.match(value.upper()):
            raise serializers.ValidationError('IFSC must look like ABCD0123456.')
        return value.upper() if value else value


class StaffDocumentSerializer(serializers.Serializer):
    """
    A file already uploaded via /global/people/documents/upload/. Only the
    reference is stored on the person — never the file bytes.
    """
    name = serializers.CharField(max_length=200, allow_blank=True, required=False)
    key = serializers.CharField(max_length=500)
    size = serializers.IntegerField(required=False, min_value=0)
    content_type = serializers.CharField(max_length=100, required=False, allow_blank=True)


class StaffProfileSerializer(serializers.Serializer):
    """Step 1 — the staff record itself."""
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    job_title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=10, required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)

    emergency_contact_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    emergency_contact_phone = serializers.CharField(max_length=10, required=False, allow_blank=True)

    aadhaar_number = serializers.CharField(max_length=12, required=False, allow_blank=True)
    pan = serializers.CharField(max_length=10, required=False, allow_blank=True)
    documents = StaffDocumentSerializer(many=True, required=False)
    bank_details = StaffBankDetailsSerializer(required=False)

    member_type = serializers.ChoiceField(
        choices=['person', 'organisation'], required=False, default='person'
    )
    staff_scope = serializers.ChoiceField(
        choices=['global', 'centre'], required=False, default='global'
    )

    def validate_name(self, value):
        # The wizard shows "Enter their name." for this case; keep parity.
        if not value.strip():
            raise serializers.ValidationError('Enter their name.')
        return value.strip()

    def _validate_phone(self, value, label):
        if value and not PHONE_RE.match(value):
            raise serializers.ValidationError(f'{label} must be 10 digits.')
        return value

    def validate_phone(self, value):
        return self._validate_phone(value, 'Phone')

    def validate_emergency_contact_phone(self, value):
        return self._validate_phone(value, 'Emergency contact phone')

    def validate_aadhaar_number(self, value):
        if value and not AADHAAR_RE.match(value.replace(' ', '')):
            raise serializers.ValidationError('Aadhaar must be 12 digits.')
        return value.replace(' ', '') if value else value

    def validate_pan(self, value):
        if value and not PAN_RE.match(value.upper()):
            raise serializers.ValidationError('PAN must look like ABCDE1234F.')
        return value.upper() if value else value


class UpdateStaffProfileSerializer(StaffProfileSerializer):
    """
    Editing an existing staff record.

    Subclasses the onboarding serializer so the validation rules — Aadhaar
    shape, PAN shape, IFSC, ten-digit phones — cannot drift between creating a
    person and correcting them afterwards.

    Every field is optional here. A PATCH fixing one phone number must not
    demand the name and email back, and the fields it does not mention are
    left alone rather than cleared. `staff_scope` is dropped because where a
    person sits follows from their role assignments, not from re-editing the
    record.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('staff_scope', None)
        for field in self.fields.values():
            field.required = False

    def validate(self, attrs):
        # Keep only what the caller actually sent. Fields carrying a default —
        # member_type defaults to 'person' — otherwise appear in validated_data
        # untouched, and a PATCH fixing a phone number would quietly rewrite an
        # organisation into a person.
        sent = {k: v for k, v in attrs.items() if k in (self.initial_data or {})}
        if not sent:
            raise serializers.ValidationError('Nothing to update.')
        return sent


class StaffRoleAssignmentSerializer(serializers.Serializer):
    """
    Step 2 — the role, and where it applies.

    Org-wide roles (Super Admin, Centre Manager, Affiliate) carry no centre.
    Centre-scoped roles (Manager, Teacher, Front desk, Sales) require one,
    and may cascade down the centre tree.
    """
    role_id = serializers.CharField()
    centre_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    include_sub_centres = serializers.BooleanField(required=False, default=False)


class OnboardStaffSerializer(serializers.Serializer):
    """The whole wizard, submitted at step 3."""
    profile = StaffProfileSerializer()
    assignment = StaffRoleAssignmentSerializer()
    send_invite = serializers.BooleanField(required=False, default=True)
