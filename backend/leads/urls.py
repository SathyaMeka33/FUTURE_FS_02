from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AuthLoginView,
    AuthLogoutView,
    EmailTemplateViewSet,
    LeadViewSet,
    TaskViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register(r"leads", LeadViewSet, basename="lead")
router.register(r"tasks", TaskViewSet, basename="task")
router.register(r"email-templates", EmailTemplateViewSet, basename="email-template")
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("auth/login/", AuthLoginView.as_view(), name="auth-login"),
    path("auth/logout/", AuthLogoutView.as_view(), name="auth-logout"),
    path("", include(router.urls)),
]
