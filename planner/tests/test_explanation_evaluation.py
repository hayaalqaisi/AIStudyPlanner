from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase

from evaluation.plan_review_cases import PLAN_REVIEW_CASES
from evaluation.plan_review_scoring import evaluate_plan_review_proposal
from evaluation.run_plan_review_evaluation import (
    build_summary,
    evaluate_case,
)
from planner.ai.plan_review_proposal_agent import ProposalGenerationError
from planner.services.plan_review_options_service import build_review_options


class ExplanationEvaluationTests(SimpleTestCase):
    def setUp(self):
        self.case = deepcopy(
            next(
                case
                for case in PLAN_REVIEW_CASES
                if case["name"] == "missed_work_finish_sooner"
            )
        )
        self.options = build_review_options(
            self.case["sessions"],
            self.case["resume_date"],
            self.case["current_daily_minutes"],
            self.case["maximum_daily_minutes"],
        )
        self.reason = (
            "The current 60 minutes per day is feasible, "
            "finishing on 2030-11-05. "
            "The selected 120 minutes per day finishes on "
            "2030-11-03, 2 days earlier. "
            "The increase is optional, rather than required "
            "for feasibility. "
            "It finishes earlier than the current-limit option, "
            "consistent with your preference to finish sooner."
        )

    def score(self, reason):
        return evaluate_plan_review_proposal(
            self.case,
            self.options,
            {
                "action": "replan_unfinished_work",
                "daily_study_minutes": 120,
                "reason": reason,
            },
        )

    def test_correct_factual_explanation_passes(self):
        result = self.score(self.reason)

        self.assertTrue(result["explanation_consistent"])
        self.assertEqual(result["explanation_error"], "")
        self.assertTrue(result["action_correct"])
        self.assertTrue(result["preference_match"])

    def test_wrong_finish_date_fails(self):
        result = self.score(
            self.reason.replace("2030-11-03", "2030-11-04")
        )

        self.assertFalse(result["explanation_consistent"])
        self.assertTrue(result["explanation_error"])

    def test_wrong_days_saved_fails(self):
        result = self.score(
            self.reason.replace("2 days earlier", "99 days earlier")
        )

        self.assertFalse(result["explanation_consistent"])

    def test_wrong_daily_limit_fails(self):
        result = self.score(
            self.reason.replace("120 minutes", "150 minutes")
        )

        self.assertFalse(result["explanation_consistent"])

    def test_capacity_contradiction_fails(self):
        result = self.score(
            self.reason + " The current limit is insufficient."
        )

        self.assertFalse(result["explanation_consistent"])

    def test_unexpected_extra_date_fails(self):
        result = self.score(
            self.reason + " Another finish date is 2030-12-01."
        )

        self.assertFalse(result["explanation_consistent"])
        self.assertIn("unexpected dates", result["explanation_error"])

    def test_unexpected_extra_number_fails(self):
        result = self.score(
            self.reason + " This saves 99 additional days."
        )

        self.assertFalse(result["explanation_consistent"])
        self.assertIn("unexpected numbers", result["explanation_error"])

    def test_generic_explanation_fails_without_invalidating_decision(self):
        result = self.score("This is a recommendation.")

        self.assertTrue(result["proposal_valid"])
        self.assertTrue(result["action_correct"])
        self.assertFalse(result["explanation_consistent"])

    def test_missing_proposal_has_inconsistent_explanation(self):
        result = evaluate_plan_review_proposal(
            self.case,
            self.options,
            None,
        )

        self.assertFalse(result["proposal_valid"])
        self.assertFalse(result["explanation_consistent"])

    @patch("evaluation.run_plan_review_evaluation.propose_plan_review")
    def test_summary_counts_failed_attempts_and_accepted_explanations(
        self,
        mock_agent,
    ):
        mock_agent.side_effect = [
            {
                "action": "replan_unfinished_work",
                "daily_study_minutes": 120,
                "reason": self.reason,
            },
            ProposalGenerationError("The AI request timed out."),
        ]

        results = [
            evaluate_case(self.case, repetition)
            for repetition in (1, 2)
        ]
        summary = build_summary(results)

        self.assertEqual(summary["consistent_explanations"], 1)
        self.assertEqual(
            summary["explanation_consistency_all_attempts"],
            0.5,
        )
        self.assertEqual(
            summary["explanation_consistency_accepted_proposals"],
            1.0,
        )

    @patch("evaluation.run_plan_review_evaluation.propose_plan_review")
    def test_accepted_bad_explanation_lowers_consistency_score(
        self,
        mock_agent,
    ):
        mock_agent.return_value = {
            "action": "replan_unfinished_work",
            "daily_study_minutes": 120,
            "reason": "A generic recommendation without scheduling facts.",
        }

        summary = build_summary([evaluate_case(self.case, 1)])

        self.assertEqual(summary["accepted_proposals"], 1)
        self.assertEqual(summary["consistent_explanations"], 0)
        self.assertEqual(
            summary["explanation_consistency_accepted_proposals"],
            0.0,
        )