from django.test import SimpleTestCase

from planner.ai.plan_review_proposal_validation import (
    ProposalValidationError,
    validate_review_proposal,
)


class ReviewProposalValidationTests(SimpleTestCase):
    def setUp(self):
        self.options = [
            {"daily_study_minutes": 90},
            {"daily_study_minutes": 120},
        ]

    def validate(
        self,
        proposal,
        *,
        options=None,
        has_unfinished_work=True,
        has_overdue_or_missed_work=True,
    ):
        return validate_review_proposal(
            proposal,
            options=self.options if options is None else options,
            has_unfinished_work=has_unfinished_work,
            has_overdue_or_missed_work=has_overdue_or_missed_work,
        )

    def test_different_feasible_limits_are_accepted(self):
        for daily_minutes in (90, 120):
            with self.subTest(daily_minutes=daily_minutes):
                result = self.validate(
                    {
                        "action": "replan_unfinished_work",
                        "daily_study_minutes": daily_minutes,
                        "reason": "A feasible workload recommendation.",
                    }
                )

                self.assertEqual(
                    result["daily_study_minutes"],
                    daily_minutes,
                )

    def test_unvalidated_limit_is_rejected(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "replan_unfinished_work",
                    "daily_study_minutes": 105,
                    "reason": "This limit was not offered.",
                }
            )

    def test_non_integer_limits_are_rejected(self):
        for daily_minutes in (True, "90", 90.5, None):
            with self.subTest(daily_minutes=daily_minutes):
                with self.assertRaises(ProposalValidationError):
                    self.validate(
                        {
                            "action": "replan_unfinished_work",
                            "daily_study_minutes": daily_minutes,
                            "reason": "Invalid limit.",
                        }
                    )

    def test_keep_is_accepted_without_overdue_or_missed_work(self):
        result = self.validate(
            {
                "action": "keep_current_plan",
                "daily_study_minutes": None,
                "reason": "  The existing schedule remains suitable.  ",
            },
            has_overdue_or_missed_work=False,
        )

        self.assertEqual(result["action"], "keep_current_plan")
        self.assertEqual(
            result["reason"],
            "The existing schedule remains suitable.",
        )

    def test_keep_is_rejected_with_overdue_or_missed_work(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "keep_current_plan",
                    "daily_study_minutes": None,
                    "reason": "Keep despite overdue work.",
                }
            )

    def test_keep_cannot_specify_a_new_limit(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "keep_current_plan",
                    "daily_study_minutes": 120,
                    "reason": "Keep the plan.",
                },
                has_overdue_or_missed_work=False,
            )

    def test_replan_is_rejected_without_unfinished_work(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "replan_unfinished_work",
                    "daily_study_minutes": 90,
                    "reason": "Reschedule completed work.",
                },
                has_unfinished_work=False,
                has_overdue_or_missed_work=False,
            )

    def test_cannot_fit_is_accepted_when_no_option_exists(self):
        result = self.validate(
            {
                "action": "cannot_fit",
                "daily_study_minutes": None,
                "reason": "No schedule fits within the allowed limit.",
            },
            options=[],
        )

        self.assertEqual(result["action"], "cannot_fit")

    def test_cannot_fit_is_rejected_when_options_exist(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "cannot_fit",
                    "daily_study_minutes": None,
                    "reason": "Incorrectly reports no feasible option.",
                }
            )

    def test_cannot_fit_is_rejected_when_all_work_is_completed(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "cannot_fit",
                    "daily_study_minutes": None,
                    "reason": "There is no unfinished work.",
                },
                options=[],
                has_unfinished_work=False,
                has_overdue_or_missed_work=False,
            )

    def test_cannot_fit_cannot_specify_a_limit(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "cannot_fit",
                    "daily_study_minutes": 120,
                    "reason": "No feasible option.",
                },
                options=[],
            )

    def test_extra_fields_are_rejected(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "replan_unfinished_work",
                    "daily_study_minutes": 90,
                    "reason": "A feasible proposal.",
                    "unexpected": True,
                }
            )

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ProposalValidationError):
            self.validate(
                {
                    "action": "delete_plan",
                    "daily_study_minutes": None,
                    "reason": "Unsupported action.",
                }
            )

    def test_invalid_reasons_are_rejected(self):
        for reason in ("", "   ", None, "x" * 1001):
            with self.subTest(reason=reason):
                with self.assertRaises(ProposalValidationError):
                    self.validate(
                        {
                            "action": "replan_unfinished_work",
                            "daily_study_minutes": 90,
                            "reason": reason,
                        }
                    )