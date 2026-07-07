from django.db import models as db_models
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
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

        # Filter by centre (query param or URL kwarg)
        centre_id = self.request.query_params.get('centre') or self.kwargs.get('centre_pk')
        if centre_id:
            queryset = queryset.filter(centre_id=centre_id)

        # Filter by session
        session_id = self.request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)

        # Search by name
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


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsApprovedUser]

    def get_queryset(self):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            return Contact.objects.filter(child_id=child_pk)
        return Contact.objects.all()

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

    def perform_create(self, serializer):
        child_pk = self.kwargs.get('child_pk')
        if child_pk:
            child = Child.objects.get(pk=child_pk)
            serializer.save(child=child)
        else:
            serializer.save()
