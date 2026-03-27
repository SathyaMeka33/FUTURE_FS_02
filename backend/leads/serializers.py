from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Activity, Attachment, EmailLog, EmailTemplate, Lead, Task

User = get_user_model()


class LeadSerializer(serializers.ModelSerializer):
    assigned_to_username = serializers.CharField(source="assigned_to.username", read_only=True)
    score = serializers.SerializerMethodField()
    sla_deadline = serializers.SerializerMethodField()
    sla_breached = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "source",
            "status",
            "priority",
            "assigned_to",
            "assigned_to_username",
            "notes",
            "first_contacted_at",
            "score",
            "sla_deadline",
            "sla_breached",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "first_contacted_at",
            "score",
            "sla_deadline",
            "sla_breached",
            "created_at",
            "updated_at",
        ]

    def get_score(self, obj: Lead) -> int:
        # Prefer queryset annotation when present.
        value = getattr(obj, "score", None)
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _sla_hours(self) -> int:
        raw = getattr(settings, "CRM_SLA_FIRST_CONTACT_HOURS", 48)
        try:
            hours = int(raw)
        except (TypeError, ValueError):
            hours = 48
        return max(1, hours)

    def get_sla_deadline(self, obj: Lead):
        return obj.created_at + timedelta(hours=self._sla_hours())

    def get_sla_breached(self, obj: Lead) -> bool:
        # Breach = still not contacted after deadline.
        if obj.first_contacted_at:
            return False
        deadline = self.get_sla_deadline(obj)
        # If created_at is naive for any reason, treat as not breached.
        try:
            from django.utils import timezone

            return timezone.now() > deadline
        except Exception:
            return False

    def validate_name(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Name is required.")
        return value.strip()

    def validate_phone(self, value: str) -> str:
        value = value.strip()
        if len(value) < 7:
            raise serializers.ValidationError("Phone number looks too short.")
        return value

    def validate_source(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Source is required.")
        return value.strip().lower()


class TaskSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    assigned_to_username = serializers.CharField(source="assigned_to.username", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "lead",
            "lead_name",
            "task_type",
            "status",
            "due_at",
            "assigned_to",
            "assigned_to_username",
            "created_by",
            "created_by_username",
            "notes",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "completed_at", "created_at", "updated_at"]


class ActivitySerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = Activity
        fields = ["id", "lead", "actor", "actor_username", "event_type", "message", "created_at"]
        read_only_fields = ["id", "actor", "created_at"]


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source="uploaded_by.username", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "lead", "uploaded_by", "uploaded_by_username", "original_name", "file", "file_url", "created_at"]
        read_only_fields = ["id", "uploaded_by", "file_url", "created_at"]

    def get_file_url(self, obj: Attachment) -> str | None:
        request = self.context.get("request")
        if not obj.file:
            return None
        if request is None:
            return obj.file.url
        return request.build_absolute_uri(obj.file.url)


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ["id", "name", "subject", "body", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmailLogSerializer(serializers.ModelSerializer):
    sent_by_username = serializers.CharField(source="sent_by.username", read_only=True)

    class Meta:
        model = EmailLog
        fields = ["id", "lead", "sent_by", "sent_by_username", "to_email", "subject", "body", "status", "created_at"]
        read_only_fields = ["id", "sent_by", "status", "created_at"]
