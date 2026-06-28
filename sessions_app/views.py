from datetime import timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from centres.models import Centre, Room
from .models import Session, SessionSlot
from .serializers import SessionSerializer, SessionSlotSerializer, GenerateSlotsSerializer


DAY_MAP = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}


def time_to_minutes(t):
    """Convert a time object to minutes since midnight."""
    return t.hour * 60 + t.minute


def has_overlap(centre_id, room_id, date, start_minutes, duration_minutes, exclude_slot_id=None):
    """Check if a proposed slot conflicts with existing ones in the same room."""
    existing = SessionSlot.objects.filter(
        centre_id=centre_id,
        room_id=room_id,
        start_date=date,
    ).select_related('session')

    if exclude_slot_id:
        existing = existing.exclude(id=exclude_slot_id)

    proposed_end = start_minutes + duration_minutes

    for slot in existing:
        slot_start = time_to_minutes(slot.start_time)
        slot_duration = slot.session.duration_total_minutes
        slot_end = slot_start + slot_duration

        if start_minutes < slot_end and proposed_end > slot_start:
            return True

    return False


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            return Session.objects.filter(centre_id=centre_pk)
        return Session.objects.all()

    def perform_create(self, serializer):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            centre = Centre.objects.get(pk=centre_pk)
            serializer.save(centre=centre)
        else:
            serializer.save()


class SessionSlotViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSlotSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        centre_pk = self.kwargs.get('centre_pk')
        queryset = SessionSlot.objects.select_related('session', 'room', 'centre')

        if centre_pk:
            queryset = queryset.filter(centre_id=centre_pk)

        # Filter by week if provided
        week = self.request.query_params.get('week')
        if week:
            from datetime import datetime
            try:
                week_start = datetime.strptime(week, '%Y-%m-%d').date()
                week_end = week_start + timedelta(days=6)
                queryset = queryset.filter(start_date__gte=week_start, start_date__lte=week_end)
            except ValueError:
                pass

        return queryset

    def perform_create(self, serializer):
        centre_pk = self.kwargs.get('centre_pk')
        if centre_pk:
            centre = Centre.objects.get(pk=centre_pk)
            serializer.save(centre=centre)
        else:
            serializer.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def generate_slots(request, centre_pk):
    """Generate recurring weekly slots (up to 15) or a single one-off slot."""
    serializer = GenerateSlotsSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        centre = Centre.objects.get(pk=centre_pk)
    except Centre.DoesNotExist:
        return Response({'detail': 'Centre not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        session = Session.objects.get(pk=data['session_id'], centre=centre)
    except Session.DoesNotExist:
        return Response({'detail': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        room = Room.objects.get(pk=data['room_id'], centre=centre)
    except Room.DoesNotExist:
        return Response({'detail': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)

    start_date = data['start_date']
    start_time = data['start_time']
    start_minutes = time_to_minutes(start_time)
    duration_minutes = session.duration_total_minutes

    if data['booking_type'] == 'one-off':
        num_slots = 1
    else:
        num_slots = 15

    # Check for overlaps first
    conflicts = []
    slot_dates = []
    for i in range(num_slots):
        slot_date = start_date + timedelta(weeks=i)
        slot_dates.append(slot_date)
        if has_overlap(centre.id, room.id, slot_date, start_minutes, duration_minutes):
            conflicts.append(str(slot_date))

    if conflicts:
        return Response(
            {
                'detail': 'Time conflicts detected.',
                'conflicts': conflicts,
            },
            status=status.HTTP_409_CONFLICT
        )

    # Create slots
    created_slots = []
    starting_month = data['starting_month']
    starting_week = data['starting_week']

    for i, slot_date in enumerate(slot_dates):
        day = DAY_MAP[slot_date.weekday()]

        slot = SessionSlot.objects.create(
            centre=centre,
            room=room,
            session=session,
            day=day,
            start_time=start_time,
            booking_type=data['booking_type'],
            start_date=slot_date,
            starting_month=starting_month,
            starting_week=starting_week,
            notes=data.get('notes', ''),
        )

        if data.get('teacher_ids'):
            slot.teachers.set(data['teacher_ids'])
        if data.get('child_ids'):
            slot.children.set(data['child_ids'])

        created_slots.append(slot)

        # Advance week/month counters
        starting_week += 1
        if starting_week > 4:
            starting_week = 1
            starting_month += 1

    result_serializer = SessionSlotSerializer(created_slots, many=True)
    return Response(result_serializer.data, status=status.HTTP_201_CREATED)
