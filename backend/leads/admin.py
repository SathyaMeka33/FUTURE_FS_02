from django.contrib import admin

from .models import Activity, Attachment, AuditLog, EmailLog, EmailTemplate, Lead, Task


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "source", "status", "priority", "assigned_to", "created_at")
    search_fields = ("name", "email", "phone", "source")
    list_filter = ("status", "priority", "source", "assigned_to", "created_at")
    ordering = ("-created_at",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("lead", "task_type", "status", "due_at", "assigned_to", "created_by")
    list_filter = ("status", "task_type", "assigned_to")
    search_fields = ("lead__name", "lead__email", "notes")
    ordering = ("due_at",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("lead", "event_type", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("lead__name", "message", "actor__username")
    ordering = ("-created_at",)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("lead", "original_name", "uploaded_by", "created_at")
    search_fields = ("lead__name", "original_name", "uploaded_by__username")
    ordering = ("-created_at",)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "updated_at")
    search_fields = ("name", "subject")
    ordering = ("name",)


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("lead", "to_email", "subject", "sent_by", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("lead__name", "to_email", "subject", "sent_by__username")
    ordering = ("-created_at",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity", "entity_id", "user", "ip_address", "created_at")
    list_filter = ("entity", "action", "created_at")
    search_fields = ("entity", "entity_id", "user__username", "ip_address")
    ordering = ("-created_at",)
