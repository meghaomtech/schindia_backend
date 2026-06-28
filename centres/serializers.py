from rest_framework import serializers
from .models import Centre, Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name']
        read_only_fields = ['id']


class CentreListSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Centre
        fields = [
            'id', 'system_id', 'name', 'street_address', 'city', 'postcode',
            'vat_number', 'phone', 'email', 'manager_name', 'rooms',
            'closure_dates', 'opening_times', 'bank_details', 'created_at',
        ]
        read_only_fields = ['id', 'system_id', 'created_at']


class CentreCreateSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, required=False)

    class Meta:
        model = Centre
        fields = [
            'id', 'system_id', 'name', 'street_address', 'city', 'postcode',
            'vat_number', 'phone', 'email', 'manager_name', 'rooms',
            'closure_dates', 'opening_times', 'bank_details',
        ]
        read_only_fields = ['id', 'system_id']

    def create(self, validated_data):
        rooms_data = validated_data.pop('rooms', [])
        centre = Centre.objects.create(**validated_data)
        for room_data in rooms_data:
            Room.objects.create(centre=centre, **room_data)
        return centre

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
