from django.conf import settings
from django.db import models


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUALIFIED = "qualified", "Qualified"
        CONVERTED = "converted", "Converted"

    class Priority(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=25)
    source = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
    )
    notes = models.TextField(blank=True)
    first_contacted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["source"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["email"]),
            models.Index(fields=["assigned_to"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"


class LeadScoreEvent(models.Model):
    """Atomic scoring events for a lead (first-time milestones, actions, etc.)."""

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="score_events")
    code = models.CharField(max_length=40)
    delta = models.SmallIntegerField()
    reason = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["lead", "code"], name="uniq_lead_score_event_code"),
        ]
        indexes = [
            models.Index(fields=["lead", "created_at"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.delta}) Lead#{self.lead_id}"


class Task(models.Model):
    class TaskType(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="tasks")
    task_type = models.CharField(max_length=10, choices=TaskType.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    due_at = models.DateTimeField()
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_assigned",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks_created",
    )
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "due_at"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["lead", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_type} for Lead#{self.lead_id} ({self.status})"


class Activity(models.Model):
    class EventType(models.TextChoices):
        LEAD_CREATED = "lead_created", "Lead created"
        STATUS_CHANGED = "status_changed", "Status changed"
        PRIORITY_CHANGED = "priority_changed", "Priority changed"
        ASSIGNED = "assigned", "Assigned"
        NOTE_UPDATED = "note_updated", "Note updated"
        TASK_CREATED = "task_created", "Task created"
        TASK_COMPLETED = "task_completed", "Task completed"
        ATTACHMENT_ADDED = "attachment_added", "Attachment added"
        EMAIL_SENT = "email_sent", "Email sent"

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead", "created_at"]), models.Index(fields=["event_type"]) ]

    def __str__(self) -> str:
        return f"{self.event_type} Lead#{self.lead_id}"


class Attachment(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments_uploaded",
    )
    file = models.FileField(upload_to="lead_attachments/%Y/%m/")
    original_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead", "created_at"]) ]


class EmailTemplate(models.Model):
    name = models.CharField(max_length=120, unique=True)
    subject = models.CharField(max_length=200)
    body = models.TextField(help_text="Use {name} / {email} placeholders.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]


class EmailLog(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="emails")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emails_sent",
    )
    to_email = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=20, default="sent")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["lead", "created_at"])]


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=80)
    entity = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=40, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["entity", "entity_id"]), models.Index(fields=["user", "created_at"]) ]
