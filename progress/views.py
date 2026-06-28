from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from schindia_auth.permissions import IsApprovedUser
from children.models import Child
from .models import JourneyEntry, ChildNote
from .serializers import JourneyEntrySerializer, ChildNoteSerializer


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
            serializer.save(child=child)
        else:
            serializer.save()


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
