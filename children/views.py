from django.db import models as db_models
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo
from .models import Child, Contact, ChildEnrolment
from .serializers import (
    ChildListSerializer,
    ChildCreateSerializer,
    ContactSerializer,
    ChildEnrolmentSerializer,
)


class ChildViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        queryset = Child.objects.prefetch_related('contacts', 'enrolments').select_related(
            'centre', 'session', 'course_progress'
        )
        centre_id = self.request.query_params.get('centre') or self.kwargs.get('centre_pk')
        if centre_id:
            queryset = queryset.filter(centre_id=centre_id)
        session_id = self.request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                db_models.Q(first_name__icontains=search) |
                db_models.Q(last_name__icontains=search)
            )
        return queryset

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ChildCreateSerializer
        return ChildListSerializer

    def list(self, request, *args, **kwargs):
        centre_pk = self.kwargs.get('centre_pk') or request.query_params.get('centre')
        if use_dynamo():
            from dynamo_backend.services import children_db
            if centre_pk:
                children = children_db.list_children(str(centre_pk))
            else:
                # Require centre filter — don't expose full table scan of children's data
                return Response(
                    {'detail': 'centre query parameter is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(children)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            child = children_db.get_child(str(kwargs['pk']))
            if not child:
                return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)
            # Scope check: if centre_pk in URL, verify child belongs to it
            centre_pk = self.kwargs.get('centre_pk')
            if centre_pk and child.get('centre_id') != str(centre_pk):
                return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(child)
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            from datetime import date, datetime

            data = request.data.copy()
            # Handle centre_id from URL or body
            if self.kwargs.get('centre_pk'):
                data['centre_id'] = str(self.kwargs['centre_pk'])
            elif data.get('centre'):
                data['centre_id'] = str(data.pop('centre'))

            # Required field validation
            required_fields = ['first_name', 'last_name', 'gender', 'date_of_birth', 'start_date']
            missing = [f for f in required_fields if not data.get(f)]
            if missing:
                return Response(
                    {f: ['This field is required.'] for f in missing},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not data.get('centre_id'):
                return Response(
                    {'centre': ['Centre is required.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate date_of_birth and start_date
            dob_str = data.get('date_of_birth')
            start_date_str = data.get('start_date')
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                if dob > date.today():
                    return Response(
                        {'date_of_birth': ['Date of birth cannot be in the future.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                if start_dt < dob:
                    return Response(
                        {'start_date': ['Start date cannot be before date of birth.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, TypeError):
                return Response(
                    {'date_of_birth': ['Invalid date format. Use YYYY-MM-DD.']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            child = children_db.create_child(data)
            return Response(child, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            child = children_db.get_child(str(kwargs['pk']))
            if not child:
                return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)
            # Scope check
            centre_pk = self.kwargs.get('centre_pk')
            if centre_pk and child.get('centre_id') != str(centre_pk):
                return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)
            updated = children_db.update_child(str(kwargs['pk']), request.data)
            return Response(updated)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db, progress_db
            child_id = str(kwargs['pk'])

            child = children_db.get_child(child_id)
            if not child:
                return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)
            # Scope check
            centre_pk = self.kwargs.get('centre_pk')
            if centre_pk and child.get('centre_id') != str(centre_pk):
                return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Cascade: delete related records to prevent orphans
            # Contacts
            for contact in children_db.list_contacts(child_id):
                children_db.delete_contact(contact['id'])
            # Enrolments (also removes child from slot child_ids)
            for enrolment in children_db.list_enrolments(child_id):
                children_db.delete_enrolment(enrolment['id'])
            # Attendance
            for record in progress_db.list_attendance(child_id):
                progress_db.delete_attendance(record['id'])
            # Journey entries
            for entry in progress_db.list_journey(child_id):
                progress_db.delete_journey_entry(entry['id'])
            # Notes
            for note in progress_db.list_notes(child_id):
                progress_db.delete_note(note['id'])

            children_db.delete_child(child_id)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            return Contact.objects.filter(child_id=child_pk)
        return Contact.objects.all()

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import children_db
            contacts = children_db.list_contacts(str(child_pk))
            return Response(contacts)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import children_db
            data = request.data.copy()

            # Required field validation for contacts
            required_fields = ['name', 'relation', 'phone', 'email']
            missing = [f for f in required_fields if not data.get(f)]
            if missing:
                return Response(
                    {f: ['This field is required.'] for f in missing},
                    status=status.HTTP_400_BAD_REQUEST
                )

            contact = children_db.create_contact(str(child_pk), data)
            return Response(contact, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            contact = children_db.get_contact(str(kwargs['pk']))
            if not contact:
                return Response({'detail': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)
            # Scope check: verify contact belongs to the child in URL
            child_pk = self.kwargs.get('child_pk')
            if child_pk and contact.get('child_id') != str(child_pk):
                return Response({'detail': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)
            updated = children_db.update_contact(str(kwargs['pk']), request.data)
            return Response(updated)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            contact = children_db.get_contact(str(kwargs['pk']))
            if not contact:
                return Response({'detail': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)
            # Scope check
            child_pk = self.kwargs.get('child_pk')
            if child_pk and contact.get('child_id') != str(child_pk):
                return Response({'detail': 'Contact not found.'}, status=status.HTTP_404_NOT_FOUND)
            children_db.delete_contact(str(kwargs['pk']))
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        child = Child.objects.get(pk=child_pk)
        serializer.save(child=child)


class EnrolmentViewSet(viewsets.ModelViewSet):
    serializer_class = ChildEnrolmentSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        queryset = ChildEnrolment.objects.select_related('slot__session', 'slot__room')
        if child_pk:
            return queryset.filter(child_id=child_pk)
        return queryset

    def list(self, request, *args, **kwargs):
        child_pk = self.kwargs.get('child_pk')
        if use_dynamo() and child_pk:
            from dynamo_backend.services import children_db
            enrolments = children_db.list_enrolments(str(child_pk))
            return Response(enrolments)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            data = request.data.copy()
            child_pk = self.kwargs.get('child_pk')
            if child_pk:
                data['child_id'] = str(child_pk)
            enrolment = children_db.create_enrolment(data)
            return Response(enrolment, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            enrolment = children_db.get_enrolment(str(kwargs['pk']))
            if not enrolment:
                return Response({'detail': 'Enrolment not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(enrolment)
        return super().retrieve(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            enrolment = children_db.get_enrolment(str(kwargs['pk']))
            if not enrolment:
                return Response({'detail': 'Enrolment not found.'}, status=status.HTTP_404_NOT_FOUND)
            updated = children_db.update_enrolment(str(kwargs['pk']), request.data)
            return Response(updated)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            enrolment = children_db.get_enrolment(str(kwargs['pk']))
            if not enrolment:
                return Response({'detail': 'Enrolment not found.'}, status=status.HTTP_404_NOT_FOUND)
            children_db.delete_enrolment(str(kwargs['pk']))
            return Response(status=status.HTTP_204_NO_CONTENT)
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            child = Child.objects.get(pk=child_pk)
            serializer.save(child=child)
        else:
            serializer.save()
