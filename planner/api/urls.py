from django.urls import path

from planner.api.course_list_api import course_list_api
from planner.api.study_plan_detail_api import study_plan_detail_api
from planner.api.study_plan_list_api import study_plan_list_api
from planner.api.study_session_status_api import study_session_status_api


app_name = "planner_api"

urlpatterns = [
    path(
        "courses/",
        course_list_api,
        name="course_list",
    ),
    path(
        "study-plans/",
        study_plan_list_api,
        name="study_plan_list",
    ),
    path(
        "study-plans/<int:plan_id>/",
        study_plan_detail_api,
        name="study_plan_detail",
    ),
    path(
        "study-sessions/<int:session_id>/status/",
        study_session_status_api,
        name="study_session_status",
    ),
]