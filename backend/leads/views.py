from __future__ import annotations

from datetime import timedelta, timezone as dt_timezone

from django.contrib.auth import authenticate, get_user_model
from django.core.mail import EmailMessage
from django.db.models import Count, Sum, Value
from django.db.models.functions import TruncDay, TruncWeek
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView

from .models import Activity, Attachment, EmailLog, EmailTemplate, Lead, Task, AuditLog, LeadScoreEvent
from .permissions import AdminOnlyPermission, LeadAccessPermission, TaskAccessPermission
from .serializers import (
    ActivitySerializer,
    AttachmentSerializer,
    EmailLogSerializer,
    EmailTemplateSerializer,
    LeadSerializer,
    TaskSerializer,
)

User = get_user_model()


def _client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _audit(request, *, action: str, entity: str, entity_id: str = "") -> None:
    try:
        AuditLog.objects.create(
            user=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id or ""),
            ip_address=_client_ip(request),
        )
    except Exception:
        # Audit logs should never break business APIs.
        return


def _activity(lead: Lead, *, actor, event_type: str, message: str = "") -> None:
    try:
        Activity.objects.create(
            lead=lead,
            actor=actor if actor and actor.is_authenticated else None,
            event_type=event_type,
            message=message[:255],
        )
    except Exception:
        return


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.select_related("assigned_to").all()
    serializer_class = LeadSerializer
    permission_classes = [LeadAccessPermission]
    filterset_fields = {
        "status": ["exact"],
        "source": ["exact"],
        "priority": ["exact"],
        "assigned_to": ["exact"],
        "created_at": ["gte", "lte"],
    }
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["created_at", "updated_at", "name", "priority"]
    ordering = ["-created_at"]

    SCORE_RULES = {
        "lead_created": (10, "Filled form"),
        "status_contacted": (20, "Contacted"),
        "status_qualified": (30, "Qualified"),
        "status_converted": (50, "Requested demo / Converted"),
    }

    def _sla_hours(self) -> int:
        from django.conf import settings

        try:
            hours = int(getattr(settings, "CRM_SLA_FIRST_CONTACT_HOURS", 48))
        except (TypeError, ValueError):
            hours = 48
        return max(1, hours)

    def _ensure_score_event(self, lead: Lead, *, code: str) -> None:
        rule = self.SCORE_RULES.get(code)
        if not rule:
            return
        delta, reason = rule
        try:
            LeadScoreEvent.objects.get_or_create(
                lead=lead,
                code=code,
                defaults={"delta": int(delta), "reason": reason},
            )
        except Exception:
            return

    def get_queryset(self):
        qs = super().get_queryset().annotate(score=Coalesce(Sum("score_events__delta"), Value(0)))
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(assigned_to=user)

    def perform_create(self, serializer):
        lead = serializer.save()
        self._ensure_score_event(lead, code="lead_created")
        _activity(lead, actor=self.request.user, event_type=Activity.EventType.LEAD_CREATED, message="Lead created")
        _audit(self.request, action="create", entity="lead", entity_id=str(lead.id))

    def perform_update(self, serializer):
        lead: Lead = self.get_object()
        old_status = lead.status
        old_priority = lead.priority
        old_assigned_to_id = lead.assigned_to_id
        old_notes = lead.notes

        updated = serializer.save()

        # SLA: set first_contacted_at when lead first becomes contacted (or beyond)
        if not updated.first_contacted_at and updated.status in [
            Lead.Status.CONTACTED,
            Lead.Status.QUALIFIED,
            Lead.Status.CONVERTED,
        ]:
            updated.first_contacted_at = timezone.now()
            updated.save(update_fields=["first_contacted_at"])

        # Scoring: first-time milestone events
        if updated.status == Lead.Status.CONTACTED:
            self._ensure_score_event(updated, code="status_contacted")
        if updated.status == Lead.Status.QUALIFIED:
            self._ensure_score_event(updated, code="status_qualified")
        if updated.status == Lead.Status.CONVERTED:
            self._ensure_score_event(updated, code="status_converted")

        if old_status != updated.status:
            _activity(
                updated,
                actor=self.request.user,
                event_type=Activity.EventType.STATUS_CHANGED,
                message=f"Status: {old_status} → {updated.status}",
            )
        if old_priority != updated.priority:
            _activity(
                updated,
                actor=self.request.user,
                event_type=Activity.EventType.PRIORITY_CHANGED,
                message=f"Priority: {old_priority} → {updated.priority}",
            )
        if old_assigned_to_id != updated.assigned_to_id:
            _activity(
                updated,
                actor=self.request.user,
                event_type=Activity.EventType.ASSIGNED,
                message="Lead assignment updated",
            )
        if (old_notes or "").strip() != (updated.notes or "").strip():
            _activity(updated, actor=self.request.user, event_type=Activity.EventType.NOTE_UPDATED, message="Notes updated")

        _audit(self.request, action="update", entity="lead", entity_id=str(updated.id))

    def perform_destroy(self, instance):
        _audit(self.request, action="delete", entity="lead", entity_id=str(instance.id))
        return super().perform_destroy(instance)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def analytics(self, request):
        total = Lead.objects.count()
        status_counts = Lead.objects.values("status").annotate(count=Count("id"))
        mapped = {item["status"]: item["count"] for item in status_counts}
        converted = mapped.get(Lead.Status.CONVERTED, 0)
        conversion_rate = (converted / total * 100) if total else 0

        sources = list(Lead.objects.values("source").annotate(count=Count("id")).order_by("-count")[:20])

        now = timezone.now()
        start_14d = now - timedelta(days=13)
        daily_qs = (
            Lead.objects.filter(created_at__gte=start_14d)
            .annotate(day=TruncDay("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        leads_daily = [{"day": item["day"].date().isoformat(), "count": item["count"]} for item in daily_qs]

        start_8w = now - timedelta(weeks=7)
        weekly_qs = (
            Lead.objects.filter(created_at__gte=start_8w)
            .annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )
        leads_weekly = [{"week": item["week"].date().isoformat(), "count": item["count"]} for item in weekly_qs]

        # SLA breaches: leads not contacted within configured SLA hours
        sla_deadline = now - timedelta(hours=self._sla_hours())
        sla_breached_count = Lead.objects.filter(first_contacted_at__isnull=True, created_at__lt=sla_deadline).count()

        return Response(
            {
                "total": total,
                "new": mapped.get(Lead.Status.NEW, 0),
                "contacted": mapped.get(Lead.Status.CONTACTED, 0),
                "qualified": mapped.get(Lead.Status.QUALIFIED, 0),
                "converted": converted,
                "conversion_rate": round(conversion_rate, 2),
                "by_source": sources,
                "leads_daily": leads_daily,
                "leads_weekly": leads_weekly,
                "sla_breached": sla_breached_count,
            }
        )

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="board")
    def board(self, request):
        """Non-paginated board feed for Kanban UI (bounded)."""
        qs = self.filter_queryset(self.get_queryset()).order_by("-created_at")
        items = list(qs[:500])
        serializer = self.get_serializer(items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def timeline(self, request, pk=None):
        lead = self.get_object()
        items = lead.activities.select_related("actor")
        return Response(ActivitySerializer(items, many=True).data)

    @action(
        detail=True,
        methods=["get", "post"],
        permission_classes=[permissions.IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser],
    )
    def attachments(self, request, pk=None):
        lead = self.get_object()
        if request.method == "GET":
            return Response(AttachmentSerializer(lead.attachments.all(), many=True, context={"request": request}).data)

        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "File is required (multipart field: file)."}, status=status.HTTP_400_BAD_REQUEST)

        att = Attachment.objects.create(
            lead=lead,
            uploaded_by=request.user,
            file=upload,
            original_name=getattr(upload, "name", "attachment"),
        )
        _activity(lead, actor=request.user, event_type=Activity.EventType.ATTACHMENT_ADDED, message=att.original_name)
        _audit(request, action="create", entity="attachment", entity_id=str(att.id))
        return Response(AttachmentSerializer(att, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def send_email(self, request, pk=None):
        lead = self.get_object()
        template_name = (request.data.get("template") or "").strip()
        subject = (request.data.get("subject") or "").strip()
        body = (request.data.get("body") or "").strip()

        if template_name:
            template = EmailTemplate.objects.filter(name=template_name).first()
            if not template:
                return Response({"detail": "Template not found."}, status=status.HTTP_400_BAD_REQUEST)
            subject = template.subject
            body = template.body

        if not subject or not body:
            return Response({"detail": "subject and body are required (or provide template)."}, status=status.HTTP_400_BAD_REQUEST)

        rendered_subject = subject.format(name=lead.name, email=lead.email)
        rendered_body = body.format(name=lead.name, email=lead.email)

        email_status = "sent"
        try:
            msg = EmailMessage(subject=rendered_subject, body=rendered_body, to=[lead.email])
            msg.send(fail_silently=False)
        except Exception as exc:
            email_status = f"error: {type(exc).__name__}"

        log = EmailLog.objects.create(
            lead=lead,
            sent_by=request.user,
            to_email=lead.email,
            subject=rendered_subject,
            body=rendered_body,
            status=email_status,
        )
        _activity(lead, actor=request.user, event_type=Activity.EventType.EMAIL_SENT, message=email_status)
        _audit(request, action="create", entity="email", entity_id=str(log.id))
        return Response(EmailLogSerializer(log).data, status=status.HTTP_201_CREATED)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related("lead", "assigned_to", "created_by").all()
    serializer_class = TaskSerializer
    permission_classes = [TaskAccessPermission]
    filterset_fields = {
        "status": ["exact"],
        "task_type": ["exact"],
        "assigned_to": ["exact"],
        "lead": ["exact"],
        "due_at": ["gte", "lte"],
    }
    search_fields = ["lead__name", "lead__email", "lead__phone", "notes"]
    ordering_fields = ["due_at", "created_at", "updated_at"]
    ordering = ["due_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(assigned_to=user)

    def perform_create(self, serializer):
        lead = Lead.objects.get(pk=serializer.validated_data["lead"].id)
        assigned_to = serializer.validated_data.get("assigned_to") or lead.assigned_to or self.request.user
        task = serializer.save(created_by=self.request.user, assigned_to=assigned_to)
        _activity(lead, actor=self.request.user, event_type=Activity.EventType.TASK_CREATED, message=task.task_type)
        _audit(self.request, action="create", entity="task", entity_id=str(task.id))

    def perform_update(self, serializer):
        task: Task = self.get_object()
        old_status = task.status
        updated: Task = serializer.save()
        if old_status != updated.status and updated.status == Task.Status.COMPLETED and not updated.completed_at:
            updated.completed_at = timezone.now()
            updated.save(update_fields=["completed_at"])
            _activity(updated.lead, actor=self.request.user, event_type=Activity.EventType.TASK_COMPLETED, message=updated.task_type)
        _audit(self.request, action="update", entity="task", entity_id=str(updated.id))

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def notifications(self, request):
        now = timezone.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        qs = self.get_queryset().filter(status=Task.Status.PENDING)
        due_today = qs.filter(due_at__gte=start, due_at__lt=end).order_by("due_at")[:50]
        overdue_count = qs.filter(due_at__lt=now).count()

        return Response(
            {
                "overdue": overdue_count,
                "due_today": TaskSerializer(due_today, many=True).data,
            }
        )

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="calendar")
    def calendar_ics(self, request):
        """Calendar integration: export upcoming pending tasks as an iCal feed."""
        now = timezone.now()
        end = now + timedelta(days=30)
        tasks = (
            self.get_queryset()
            .filter(status=Task.Status.PENDING, due_at__gte=now, due_at__lte=end)
            .select_related("lead")
            .order_by("due_at")
        )

        def dt(dtobj):
            # UTC time in basic format
            return dtobj.astimezone(dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Mini CRM//Tasks//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        for t in tasks:
            uid = f"task-{t.id}@mini-crm"
            summary = f"{t.get_task_type_display()} — {t.lead.name}"
            lines.extend(
                [
                    "BEGIN:VEVENT",
                    f"UID:{uid}",
                    f"DTSTAMP:{dt(now)}",
                    f"DTSTART:{dt(t.due_at)}",
                    f"SUMMARY:{summary}",
                    f"DESCRIPTION:Lead: {t.lead.email}",
                    "END:VEVENT",
                ]
            )

        lines.append("END:VCALENDAR")

        from django.http import HttpResponse

        resp = HttpResponse("\r\n".join(lines) + "\r\n", content_type="text/calendar")
        resp["Content-Disposition"] = "attachment; filename=mini-crm-tasks.ics"
        return resp


class EmailTemplateViewSet(viewsets.ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [AdminOnlyPermission]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["name"]


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "is_staff"]


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return super().get_queryset()
        return User.objects.filter(id=user.id)


class AuthLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request=request, username=username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "username": user.username,
            },
            status=status.HTTP_200_OK,
        )


class AuthLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)
