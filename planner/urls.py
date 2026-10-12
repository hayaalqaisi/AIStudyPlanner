from django.urls import path

from planner.views.agent_log_list_view import agent_log_list_view
from planner.views.course_create_view import course_create_view
from planner.views.course_delete_view import course_delete_view
from planner.views.course_list_view import course_list_view
from planner.views.course_update_view import course_update_view
from planner.views.exam_create_view import exam_create_view
from planner.views.exam_delete_view import exam_delete_view
from planner.views.exam_list_view import exam_list_view
from planner.views.exam_update_view import exam_update_view
from planner.views.home_view import home_view
from planner.views.plan_review_view import plan_review_view
from planner.views.study_plan_archive_view import study_plan_archive_view
from planner.views.study_plan_create_view import study_plan_create_view
from planner.views.study_plan_detail_view import study_plan_detail_view
from planner.views.study_plan_list_view import study_plan_list_view
from planner.views.study_plan_replan_view import study_plan_replan_view
from planner.views.study_preference_view import study_preference_view
from planner.views.study_session_status_view import study_session_status_view
from planner.views.syllabus_download_view import syllabus_download_view
from planner.views.syllabus_list_view import syllabus_list_view
from planner.views.syllabus_text_view import syllabus_text_view
from planner.views.syllabus_upload_view import syllabus_upload_view
from planner.views.topic_duration_view import topic_duration_view
from planner.views.topic_generate_view import topic_generate_view
from planner.views.topic_list_view import topic_list_view


app_name = "planner"

urlpatterns = [
    path("", home_view, name="home"),
    path(
        "study-settings/",
        study_preference_view,
        name="study_preferences",
    ),
    path(
        "agent-history/",
        agent_log_list_view,
        name="agent_log_list",
    ),
    path(
        "study-plans/",
        study_plan_list_view,
        name="study_plan_list",
    ),
    path(
        "study-plans/generate/",
        study_plan_create_view,
        name="study_plan_create",
    ),
    path(
        "study-plans/<int:plan_id>/",
        study_plan_detail_view,
        name="study_plan_detail",
    ),
    path(
        "study-plans/<int:plan_id>/archive/",
        study_plan_archive_view,
        name="study_plan_archive",
    ),
    path(
        "study-plans/<int:plan_id>/replan/",
        study_plan_replan_view,
        name="study_plan_replan",
    ),
    path(
        "study-plans/<int:plan_id>/review/",
        plan_review_view,
        name="plan_review",
    ),
    path(
        "study-sessions/<int:session_id>/status/",
        study_session_status_view,
        name="study_session_status",
    ),
    path("courses/", course_list_view, name="course_list"),
    path("courses/add/", course_create_view, name="course_create"),
    path(
        "courses/<int:course_id>/edit/",
        course_update_view,
        name="course_update",
    ),
    path(
        "courses/<int:course_id>/delete/",
        course_delete_view,
        name="course_delete",
    ),
    path(
        "courses/<int:course_id>/syllabi/",
        syllabus_list_view,
        name="syllabus_list",
    ),
    path(
        "courses/<int:course_id>/syllabi/upload/",
        syllabus_upload_view,
        name="syllabus_upload",
    ),
    path(
        "syllabi/<int:syllabus_id>/download/",
        syllabus_download_view,
        name="syllabus_download",
    ),
    path(
        "syllabi/<int:syllabus_id>/text/",
        syllabus_text_view,
        name="syllabus_text",
    ),
    path(
        "syllabi/<int:syllabus_id>/topics/",
        topic_list_view,
        name="topic_list",
    ),
    path(
        "syllabi/<int:syllabus_id>/topics/generate/",
        topic_generate_view,
        name="topic_generate",
    ),
    path(
        "topics/<int:topic_id>/study-time/",
        topic_duration_view,
        name="topic_duration",
    ),
    path(
        "courses/<int:course_id>/exams/",
        exam_list_view,
        name="exam_list",
    ),
    path(
        "courses/<int:course_id>/exams/add/",
        exam_create_view,
        name="exam_create",
    ),
    path(
        "exams/<int:exam_id>/edit/",
        exam_update_view,
        name="exam_update",
    ),
    path(
        "exams/<int:exam_id>/delete/",
        exam_delete_view,
        name="exam_delete",
    ),
]