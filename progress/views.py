from datetime import timedelta, date

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo
from children.models import Child
from .models import JourneyEntry, ChildNote, Attendance, CourseProgress
from .serializers import (
    JourneyEntrySerializer,
    ChildNoteSerializer,
    AttendanceSerializer,
    CourseProgressSerializer,
)


class JourneyEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JourneyEntrySerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            return JourneyEntry.objects.filter(child_id=child_pk)
        return JourneyEntry.objects.all()

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            child = Child.objects.get(pk=child_pk)
            entry = serializer.save(child=child)
        else:
            entry = serializer.save()

        # Send milestone/observation notification to parents (Req 25.3)
        from billing.notifications import send_milestone_notification
        send_milestone_notification(entry)

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            entries = progress_db.list_journey(str(child_pk))
            return Response(entries)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            data = request.data.copy()
            data['date'] = data.get('date', date.today().isoformat())
            entry = progress_db.create_journey_entry(str(child_pk), data)
            return Response(entry, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)


class ChildNoteViewSet(viewsets.ModelViewSet):
    serializer_class = ChildNoteSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            return ChildNote.objects.filter(child_id=child_pk)
        return ChildNote.objects.all()

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            child = Child.objects.get(pk=child_pk)
            serializer.save(child=child)
        else:
            serializer.save()

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            notes = progress_db.list_notes(str(child_pk))
            return Response(notes)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            data = request.data.copy()
            data['date'] = data.get('date', date.today().isoformat())
            note = progress_db.create_note(str(child_pk), data)
            return Response(note, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        queryset = Attendance.objects.select_related('session', 'teacher', 'slot')

        if child_pk:
            queryset = queryset.filter(child_id=child_pk)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            child = Child.objects.get(pk=child_pk)
            attendance = serializer.save(child=child)
        else:
            attendance = serializer.save()

        # Send attendance notification to parents (Req 25.1)
        from billing.notifications import send_attendance_notification
        send_attendance_notification(attendance)

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            date_from = request.query_params.get('date_from')
            date_to = request.query_params.get('date_to')
            records = progress_db.list_attendance(str(child_pk), date_from, date_to)
            return Response(records)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            data = request.data.copy()
            data['date'] = data.get('date', date.today().isoformat())
            record = progress_db.create_attendance(str(child_pk), data)

            # Send notification
            from billing.notifications import send_attendance_notification
            # For DynamoDB mode, pass the record directly
            # (notification function handles both ORM and dict)
            return Response(record, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)


class CourseProgressViewSet(viewsets.ModelViewSet):
    serializer_class = CourseProgressSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            return CourseProgress.objects.filter(child_id=child_pk)
        return CourseProgress.objects.all()

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            child = Child.objects.get(pk=child_pk)
            serializer.save(child=child)
        else:
            serializer.save()

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            progress = progress_db.get_course_progress(str(child_pk))
            return Response([progress] if progress else [])
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import progress_db
            data = request.data.copy()
            progress = progress_db.set_course_progress(str(child_pk), data)
            return Response(progress, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def child_activity_feed(request, child_pk):
    """Unified activity timeline for a child (Req 13.5)."""
    if use_dynamo():
        from dynamo_backend.services import progress_db, children_db
        child = children_db.get_child(str(child_pk))
        if not child:
            return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)

        activities = progress_db.get_activity_feed(str(child_pk), limit=20)

        # Add registration event
        activities.append({
            'type': 'registration',
            'date': child.get('start_date', child.get('created_at', '')[:10]),
            'text': f"Registered Joined centre",
            'created_at': child.get('created_at', ''),
        })
        activities.sort(key=lambda x: x.get('date', ''), reverse=True)
        return Response(activities)

    # Django ORM path
    try:
        child = Child.objects.select_related('centre').get(pk=child_pk)
    except Child.DoesNotExist:
        return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)

    activities = []

    # Attendance records
    attendances = Attendance.objects.filter(
        child=child
    ).select_related('session', 'teacher').order_by('-date')[:20]

    for att in attendances:
        teacher_name = att.teacher.get_full_name() if att.teacher else 'Unknown'
        activities.append({
            'type': 'attendance',
            'date': att.date.isoformat(),
            'text': f"Attended {att.session.name} with {teacher_name}",
            'status': att.status,
            'created_at': att.created_at.isoformat(),
        })

    # Journey entries
    journey_entries = JourneyEntry.objects.filter(child=child).order_by('-date')[:20]
    for entry in journey_entries:
        activities.append({
            'type': entry.type.lower(),
            'date': entry.date.isoformat(),
            'text': f"{entry.type}: {entry.text}",
            'staff_name': entry.staff_name,
            'created_at': entry.created_at.isoformat(),
        })

    # Notes
    notes = ChildNote.objects.filter(child=child).order_by('-date')[:20]
    for note in notes:
        activities.append({
            'type': 'note',
            'date': note.date.isoformat(),
            'text': f"Note added {note.text}",
            'staff_name': note.staff_name,
            'created_at': note.created_at.isoformat(),
        })

    # Registration event
    activities.append({
        'type': 'registration',
        'date': child.start_date.isoformat(),
        'text': f"Registered Joined {child.centre.name}",
        'created_at': child.created_at.isoformat(),
    })

    activities.sort(key=lambda x: x['date'], reverse=True)
    return Response(activities)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def child_stats(request, child_pk):
    """Summary stats for a child (Req 13.4)."""
    if use_dynamo():
        from dynamo_backend.services import progress_db, children_db
        child = children_db.get_child(str(child_pk))
        if not child:
            return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)
        stats = progress_db.get_child_stats(str(child_pk))
        return Response(stats)

    # Django ORM path
    try:
        child = Child.objects.get(pk=child_pk)
    except Child.DoesNotExist:
        return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)

    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    sessions_this_week = Attendance.objects.filter(
        child=child, date__gte=week_start, date__lte=week_end, status='attended',
    ).count()

    total_sessions = Attendance.objects.filter(child=child, status='attended').count()
    journey_entries_count = JourneyEntry.objects.filter(child=child).count()

    try:
        progress = CourseProgress.objects.get(child=child)
        course_progress = progress.display
    except CourseProgress.DoesNotExist:
        course_progress = 'M1 W1'

    return Response({
        'sessions_this_week': sessions_this_week,
        'total_sessions': total_sessions,
        'journey_entries': journey_entries_count,
        'course_progress': course_progress,
    })
