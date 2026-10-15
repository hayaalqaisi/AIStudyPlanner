from django.contrib import admin

from planner.models import (
    AgentLog,
    Course,
    Exam,
    StudyPlan,
    StudySession,
    Syllabus,
    Topic,
)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Allow inspection while preventing changes through the admin."""

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Course)
class CourseAdmin(ReadOnlyAdmin):
    list_display = ("id", "name", "user", "created_at")
    search_fields = ("name", "user__username")
    list_select_related = ("user",)
    ordering = ("name", "id")


@admin.register(Exam)
class ExamAdmin(ReadOnlyAdmin):
    list_display = ("id", "title", "course", "exam_date")
    search_fields = ("title", "course__name", "course__user__username")
    date_hierarchy = "exam_date"
    list_select_related = ("course",)
    ordering = ("exam_date", "id")


@admin.register(Syllabus)
class SyllabusAdmin(ReadOnlyAdmin):
    list_display = ("id", "original_filename", "course", "uploaded_at")
    search_fields = (
        "original_filename",
        "course__name",
        "course__user__username",
    )
    fields = ("id", "course", "original_filename", "uploaded_at")
    list_select_related = ("course",)
    ordering = ("-uploaded_at", "-id")


@admin.register(Topic)
class TopicAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "title",
        "syllabus",
        "position",
        "estimated_study_minutes",
    )
    search_fields = (
        "title",
        "syllabus__course__name",
        "syllabus__course__user__username",
    )
    list_select_related = ("syllabus__course",)
    ordering = ("syllabus_id", "position", "id")


@admin.register(StudyPlan)
class StudyPlanAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "start_date",
        "resume_date",
        "daily_study_minutes",
    )
    list_filter = ("status",)
    search_fields = ("user__username",)
    list_select_related = ("user",)
    ordering = ("-created_at", "-id")


@admin.register(StudySession)
class StudySessionAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "plan",
        "course_name",
        "topic_title",
        "study_date",
        "duration_minutes",
        "kind",
        "status",
    )
    list_filter = ("status", "kind")
    search_fields = (
        "course_name",
        "topic_title",
        "exam_title",
        "plan__user__username",
    )
    date_hierarchy = "study_date"
    list_select_related = ("plan",)
    ordering = ("study_date", "id")


@admin.register(AgentLog)
class AgentLogAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "user",
        "plan",
        "action",
        "outcome",
        "duration_ms",
        "created_at",
    )
    list_filter = ("action", "outcome")
    search_fields = (
        "user__username",
        "decision_reason",
        "result_message",
    )
    date_hierarchy = "created_at"
    list_select_related = ("user", "plan")
    ordering = ("-created_at", "-id")