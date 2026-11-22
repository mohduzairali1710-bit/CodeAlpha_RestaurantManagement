from rest_framework.permissions import BasePermission


class IsStaffUser(BasePermission):
    """Restrict operational data and reports to Django staff accounts."""

    message = "Staff access is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
