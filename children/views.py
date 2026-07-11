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
        queryset = Child.objects.prefetch_related('contacts').select_related('centre', 'session')
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
        if use_dynamo() and centre_pk:
            from dynamo_backend.services import children_db
            children = children_db.list_children(str(centre_pk))
            return Response(children)
        elif use_dynamo():
            from dynamo_backend.services import children_db
            children = children_db.list_children()
            return Response(children)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            child = children_db.get_child(str(kwargs['pk']))
            if not child:
                return Response({'detail': 'Child not found.'}, status=status.HTTP_404_NOT_FOUND)
            return Response(child)
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            data = request.data.copy()
            if self.kwargs.get('centre_pk'):
                data['centre_id'] = str(self.kwargs['centre_pk'])
            child = children_db.create_child(data)
            return Response(child, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            child = children_db.update_child(str(kwargs['pk']), request.data)
            return Response(child)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            children_db.delete_child(str(kwargs['pk']))
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
            contact = children_db.create_contact(str(child_pk), request.data.copy())
            return Response(contact, status=status.HTTP_201_CREATED)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
            contact = children_db.update_contact(str(kwargs['pk']), request.data)
            return Response(contact)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
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
        if child_pk:
            return ChildEnrolment.objects.filter(child_id=child_pk)
        return ChildEnrolment.objects.all()

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

    def destroy(self, request, *args, **kwargs):
        if use_dynamo():
            from dynamo_backend.services import children_db
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
