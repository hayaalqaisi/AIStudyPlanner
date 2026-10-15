import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from planner.models import Course, StudyPlan, StudySession, Syllabus


class OwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="course_owner",
            password="Owner-Test-Password-2030!",
        )
        cls.other_user = User.objects.create_user(
            username="other_student",
            password="Other-Test-Password-2030!",
        )
        cls.course = Course.objects.create(
            user=cls.owner,
            name="Database Systems",
            description="Original course description.",
        )
        cls.syllabus = Syllabus.objects.create(
            course=cls.course,
            file="syllabi/ownership-test.txt",
            original_filename="ownership-test.txt",
        )
        cls.plan = StudyPlan.objects.create(
            user=cls.owner,
            start_date=date(2030, 11, 1),
            daily_study_minutes=120,
        )
        cls.session = StudySession.objects.create(
            plan=cls.plan,
            course_name=cls.course.name,
            topic_title="SQL queries",
            exam_title="Final exam",
            exam_date=date(2030, 11, 15),
            study_date=date(2030, 11, 1),
            duration_minutes=60,
            kind=StudySession.Kind.STUDY,
            status=StudySession.Status.PENDING,
        )

    def setUp(self):
        self.client.force_login(self.other_user)

    def test_other_users_course_edit_page_returns_404(self):
        response = self.client.get(
            reverse(
                "planner:course_update",
                args=[self.course.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_other_users_course_cannot_be_updated(self):
        response = self.client.post(
            reverse(
                "planner:course_update",
                args=[self.course.pk],
            ),
            {
                "name": "Unauthorized change",
                "description": "This must not be saved.",
            },
        )

        self.assertEqual(response.status_code, 404)

        self.course.refresh_from_db()

        self.assertEqual(self.course.name, "Database Systems")
        self.assertEqual(
            self.course.description,
            "Original course description.",
        )
        self.assertEqual(self.course.user_id, self.owner.pk)

    def test_courses_api_excludes_other_users_courses(self):
        response = self.client.get(
            reverse("planner_api:course_list")
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["count"], 0)
        self.assertEqual(data["data"]["courses"], [])

    def test_other_users_syllabus_download_returns_404(self):
        response = self.client.get(
            reverse(
                "planner:syllabus_download",
                args=[self.syllabus.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_other_users_syllabus_topics_return_404(self):
        response = self.client.get(
            reverse(
                "planner:topic_list",
                args=[self.syllabus.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_other_users_plan_page_returns_404(self):
        response = self.client.get(
            reverse(
                "planner:study_plan_detail",
                args=[self.plan.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_other_users_plan_api_returns_404(self):
        response = self.client.get(
            reverse(
                "planner_api:study_plan_detail",
                args=[self.plan.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])

    def test_plans_api_excludes_other_users_plans(self):
        response = self.client.get(
            reverse("planner_api:study_plan_list")
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["count"], 0)
        self.assertEqual(data["data"]["plans"], [])

    def test_other_users_session_page_returns_404(self):
        response = self.client.get(
            reverse(
                "planner:study_session_status",
                args=[self.session.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_other_users_session_cannot_be_updated_through_view(self):
        response = self.client.post(
            reverse(
                "planner:study_session_status",
                args=[self.session.pk],
            ),
            {"status": "completed"},
        )

        self.assertEqual(response.status_code, 404)

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.status,
            StudySession.Status.PENDING,
        )

    def test_other_users_session_cannot_be_updated_through_api(self):
        response = self.client.patch(
            reverse(
                "planner_api:study_session_status",
                args=[self.session.pk],
            ),
            data=json.dumps({"status": "completed"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()["success"])

        self.session.refresh_from_db()

        self.assertEqual(
            self.session.status,
            StudySession.Status.PENDING,
        )