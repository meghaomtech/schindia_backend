from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Child, Contact, ChildEnrolment


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'id', 'name', 'relation', 'phone', 'email',
            'invite_as', 'is_main', 'is_bill_payer', 'is_emergency',
        ]
        read_only_fields = ['id']

    def validate(self, data):
        is_main = data.get('is_main', False)
        if is_main:
            if not data.get('name'):
                raise serializers.ValidationError({'name': 'Name is required for main contact.'})
            if not data.get('email'):
                raise serializers.ValidationError({'email': 'Email is required for main contact.'})
            if not data.get('phone'):
                raise serializers.ValidationError({'phone': 'Phone is required for main contact.'})
            if not data.get('relation'):
                raise serializers.ValidationError({'relation': 'Relation is required for main contact.'})
        return data


class ChildListSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, read_only=True)
    session_name = serializers.CharField(source='session.name', read_only=True, default=None)
    centre_name = serializers.CharField(source='centre.name', read_only=True)
    age_display = serializers.SerializerMethodField()
    course_progress = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = [
            'id', 'system_id', 'first_name', 'middle_name', 'last_name',
            'gender', 'centre', 'centre_name', 'session', 'session_name',
            'date_of_birth', 'start_date', 'sibling', 'contacts',
            'age_display', 'course_progress', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'system_id', 'created_at']

    def get_age_display(self, obj):
        from datetime import date
        today = date.today()
        delta = today - obj.date_of_birth
        years = delta.days // 365
        months = (delta.days % 365) // 30
        if years > 0:
            parts = [f"{years} year{'s' if years != 1 else ''}"]
            if months > 0:
                parts.append(f"{months} month{'s' if months != 1 else ''}")
            return ', '.join(parts)
        return f"{months} month{'s' if months != 1 else ''}"

    def get_course_progress(self, obj):
        try:
            from progress.models import CourseProgress
            progress = CourseProgress.objects.get(child=obj)
            return progress.display
        except Exception:
            return 'M1 W1'

    def get_status(self, obj):
        # Active if child has a session assigned
        return 'Active' if obj.session else 'Inactive'


class ChildCreateSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, required=False)

    class Meta:
        model = Child
        fields = [
            'id', 'system_id', 'first_name', 'middle_name', 'last_name',
            'gender', 'centre', 'session', 'date_of_birth', 'start_date',
            'sibling', 'contacts',
        ]
        read_only_fields = ['id', 'system_id']

    def validate(self, data):
        contacts = data.get('contacts', [])
        # At least one main contact required on creation
        if self.instance is None:  # Only on create
            has_main = any(c.get('is_main', False) for c in contacts)
            if contacts and not has_main:
                raise serializers.ValidationError(
                    {'contacts': 'At least one contact must be marked as main.'}
                )
        return data

    def create(self, validated_data):
        contacts_data = validated_data.pop('contacts', [])
        child = Child.objects.create(**validated_data)
        for contact_data in contacts_data:
            Contact.objects.create(child=child, **contact_data)
        return child

    def update(self, instance, validated_data):
        contacts_data = validated_data.pop('contacts', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class ChildEnrolmentSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source='slot.session.name', read_only=True)
    room_name = serializers.CharField(source='slot.room.name', read_only=True)
    day = serializers.CharField(source='slot.day', read_only=True)
    start_time = serializers.TimeField(source='slot.start_time', read_only=True)

    class Meta:
        model = ChildEnrolment
        fields = [
            'id', 'child', 'slot', 'start_date', 'end_date',
            'session_name', 'room_name', 'day', 'start_time', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
