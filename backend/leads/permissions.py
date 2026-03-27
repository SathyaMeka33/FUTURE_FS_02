from rest_framework.permissions import SAFE_METHODS, BasePermission


class LeadAccessPermission(BasePermission):
    """Role model:

    - Public: can create leads (POST).
    - Admin (is_staff): full access.
    - Sales agent (authenticated, not staff): can only access leads assigned to them.
    """

    def has_permission(self, request, view):
        if request.method == "POST":
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method == "POST":
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return getattr(obj, "assigned_to_id", None) == user.id


class TaskAccessPermission(BasePermission):
    """Admins can access all tasks; agents only their assigned tasks."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        return getattr(obj, "assigned_to_id", None) == user.id


class AdminOnlyPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))
