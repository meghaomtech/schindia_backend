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

    class Meta:
        model = Child
        fields = [
            'id', 'system_id', 'first_name', 'middle_name', 'last_name',
            'gender', 'centre', 'session', 'date_of_birth', 'start_date',
            'sibling', 'contacts', 'created_at',
        ]
        read_only_fields = ['id', 'system_id', 'created_at']


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
    class Meta:
        model = ChildEnrolment
        fields = ['id', 'child', 'slot', 'start_date', 'end_date', 'created_at']
        read_only_fields = ['id', 'created_at']
