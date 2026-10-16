from django.test import SimpleTestCase

from planner.ai.plan_review_proposal_validation import (
    ProposalValidationError,
    validate_explanation_claim,
)


class ExplanationClaimTests(SimpleTestCase):
    def setUp(self):
        self.options = [
            {"daily_study_minutes": 60},
            {"daily_study_minutes": 120},
        ]
        self.proposal = {
            "action": "replan_unfinished_work",
            "daily_study_minutes": 120,
            "reason": (
                "The higher daily limit finishes earlier, "
                "matching your preference to finish sooner."
            ),
        }

    def validate(self, claim, *, options=None):
        return validate_explanation_claim(
            self.proposal,
            limit_change_type=claim,
            current_daily_minutes=60,
            options=self.options if options is None else options,
        )

    def test_optional_increase_is_accepted_as_preference(self):
        self.assertEqual(
            self.validate("preference"),
            "preference",
        )

    def test_feasible_current_limit_cannot_require_increase(self):
        with self.assertRaisesMessage(
            ProposalValidationError,
            "an increase cannot be described as required",
        ):
            self.validate("required")

    def test_unchanged_limit_is_accepted_as_not_needed(self):
        self.proposal["daily_study_minutes"] = 60
        self.proposal["reason"] = (
            "Reschedule the unfinished work using the current daily limit."
        )

        self.assertEqual(
            self.validate("not_needed"),
            "not_needed",
        )

    def test_unchanged_limit_cannot_be_classified_as_preference(self):
        self.proposal["daily_study_minutes"] = 60

        with self.assertRaisesMessage(
            ProposalValidationError,
            "Expected 'not_needed'",
        ):
            self.validate("preference")

    def test_increase_is_required_when_current_limit_is_not_feasible(self):
        self.assertEqual(
            self.validate(
                "required",
                options=[{"daily_study_minutes": 120}],
            ),
            "required",
        )

    def test_required_increase_cannot_be_classified_as_preference(self):
        with self.assertRaisesMessage(
            ProposalValidationError,
            "Expected 'required'",
        ):
            self.validate(
                "preference",
                options=[{"daily_study_minutes": 120}],
            )

    def test_non_replanning_actions_do_not_propose_limit_changes(self):
        for action in ("keep_current_plan", "cannot_fit"):
            with self.subTest(action=action):
                self.proposal["action"] = action
                self.proposal["daily_study_minutes"] = None

                self.assertEqual(
                    self.validate("not_needed", options=[]),
                    "not_needed",
                )

                with self.assertRaises(ProposalValidationError):
                    self.validate("preference", options=[])

    def test_unsupported_claim_type_is_rejected(self):
        with self.assertRaisesMessage(
            ProposalValidationError,
            "unsupported limit change type",
        ):
            self.validate("mandatory")

    def test_known_capacity_contradictions_are_rejected(self):
        reasons = [
            "The current limit cannot accommodate the work.",
            "The current limit can't accommodate the work.",
            "The current limit is insufficient.",
            "The current limit is not enough.",
            "The current limit won't meet the deadline.",
            "The current limit is unable to accommodate the work.",
            "The current limit won\u2019t meet the deadline.",
            "The current limit is NOT   ENOUGH.",
        ]

        for reason in reasons:
            with self.subTest(reason=reason):
                self.proposal["reason"] = reason

                with self.assertRaisesMessage(
                    ProposalValidationError,
                    "without claiming",
                ):
                    self.validate("preference")

    def test_capacity_warning_is_allowed_when_increase_is_required(self):
        self.proposal["reason"] = (
            "The current daily limit is insufficient; "
            "the selected higher limit provides a feasible replacement."
        )

        self.assertEqual(
            self.validate(
                "required",
                options=[{"daily_study_minutes": 120}],
            ),
            "required",
        )