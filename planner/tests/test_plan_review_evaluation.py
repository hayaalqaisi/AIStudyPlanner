from django.test import SimpleTestCase

from evaluation.plan_review_cases import PLAN_REVIEW_CASES
from evaluation.plan_review_scoring import (
    evaluate_plan_review_proposal,
)
from planner.services.plan_review_options_service import (
    build_review_options,
)


class PlanReviewEvaluationTests(SimpleTestCase):
    def setUp(self):
        self.cases = {
            case["name"]: case
            for case in PLAN_REVIEW_CASES
        }

    def options_for(self, case):
        return build_review_options(
            case["sessions"],
            case["resume_date"],
            case["current_daily_minutes"],
            case["maximum_daily_minutes"],
        )

    def proposal(self, action, daily_minutes=None):
        return {
            "action": action,
            "daily_study_minutes": daily_minutes,
            "reason": "A recommendation for the supplied scenario.",
        }

    def test_lighter_workload_rubric_accepts_lowest_limit(self):
        case = self.cases["missed_work_lighter_workload"]

        result = evaluate_plan_review_proposal(
            case,
            self.options_for(case),
            self.proposal("replan_unfinished_work", 60),
        )

        self.assertTrue(result["proposal_valid"])
        self.assertTrue(result["action_correct"])
        self.assertTrue(result["preference_match"])
        self.assertEqual(result["rubric_daily_minutes"], 60)

    def test_finish_sooner_rubric_accepts_earliest_finish(self):
        case = self.cases["missed_work_finish_sooner"]

        result = evaluate_plan_review_proposal(
            case,
            self.options_for(case),
            self.proposal("replan_unfinished_work", 120),
        )

        self.assertTrue(result["proposal_valid"])
        self.assertTrue(result["action_correct"])
        self.assertTrue(result["preference_match"])
        self.assertEqual(result["rubric_daily_minutes"], 120)

    def test_safe_choice_can_fail_preference_rubric(self):
        case = self.cases["missed_work_finish_sooner"]

        result = evaluate_plan_review_proposal(
            case,
            self.options_for(case),
            self.proposal("replan_unfinished_work", 60),
        )

        self.assertTrue(result["proposal_valid"])
        self.assertTrue(result["action_correct"])
        self.assertFalse(result["preference_match"])

    def test_unoffered_limit_is_invalid(self):
        case = self.cases["missed_work_finish_sooner"]

        result = evaluate_plan_review_proposal(
            case,
            self.options_for(case),
            self.proposal("replan_unfinished_work", 121),
        )

        self.assertFalse(result["proposal_valid"])
        self.assertFalse(result["action_correct"])
        self.assertFalse(result["preference_match"])
        self.assertTrue(result["validation_error"])

    def test_completed_plan_has_no_preference_score(self):
        case = self.cases["completed_plan_kept"]

        result = evaluate_plan_review_proposal(
            case,
            self.options_for(case),
            self.proposal("keep_current_plan"),
        )

        self.assertTrue(result["proposal_valid"])
        self.assertTrue(result["action_correct"])
        self.assertFalse(result["preference_applicable"])
        self.assertIsNone(result["preference_match"])

    def test_capacity_and_deadline_failures_expect_cannot_fit(self):
        for name in (
            "maximum_limit_insufficient",
            "exam_deadline_reached",
        ):
            with self.subTest(case=name):
                case = self.cases[name]
                options = self.options_for(case)

                self.assertEqual(options, [])

                result = evaluate_plan_review_proposal(
                    case,
                    options,
                    self.proposal("cannot_fit"),
                )

                self.assertTrue(result["proposal_valid"])
                self.assertTrue(result["action_correct"])
                self.assertIsNone(result["preference_match"])

    def test_completed_work_is_counted_in_required_limit(self):
        case = self.cases["completed_work_requires_higher_limit"]
        options = self.options_for(case)

        self.assertEqual(
            [option["daily_study_minutes"] for option in options],
            [90, 105, 120],
        )

        result = evaluate_plan_review_proposal(
            case,
            options,
            self.proposal("replan_unfinished_work", 90),
        )

        self.assertTrue(result["proposal_valid"])
        self.assertTrue(result["action_correct"])
        self.assertTrue(result["preference_match"])
        self.assertEqual(result["rubric_daily_minutes"], 90)