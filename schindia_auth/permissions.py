from rest_framework.permissions import BasePermission


class IsRootUser(BasePermission):
    """Only allows access to root users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'root'
        )


class IsApprovedUser(BasePermission):
    """Only allows access to approved users."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.status == 'approved'
        )
