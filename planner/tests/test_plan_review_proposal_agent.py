import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from planner.ai.openai_client import AIServiceError
from planner.ai.plan_review_proposal_agent import (
    ProposalGenerationError,
    propose_plan_review,
)
from planner.ai.plan_review_proposal_tools import (
    PLAN_REVIEW_PROPOSAL_TOOLS,
)


class ReviewProposalAgentTests(SimpleTestCase):
    def setUp(self):
        self.arguments = {
            "progress": {
                "completed_minutes": 30,
                "pending_minutes": 180,
                "missed_minutes": 60,
                "overdue_pending_minutes": 30,
            },
            "options": [
                {
                    "daily_study_minutes": 90,
                    "finish_date": "2030-11-05",
                    "study_days": 3,
                    "peak_daily_minutes": 90,
                },
                {
                    "daily_study_minutes": 120,
                    "finish_date": "2030-11-04",
                    "study_days": 2,
                    "peak_daily_minutes": 120,
                },
            ],
            "preference": "manageable_workload",
            "current_daily_minutes": 60,
            "maximum_daily_minutes": 120,
            "resume_date": date(2030, 11, 2),
        }

    def response(self, proposal):
        return SimpleNamespace(
            status="completed",
            output=[
                SimpleNamespace(
                    type="function_call",
                    name="submit_review_proposal",
                    arguments=json.dumps(proposal),
                ),
            ],
        )

    def replan_proposal(self, daily_minutes=90):
        return {
            "action": "replan_unfinished_work",
            "daily_study_minutes": daily_minutes,
            "limit_change_type": "required",
            "reason": "A feasible workload recommendation.",
        }

    def add_current_limit_option(self):
        self.arguments["options"].insert(
            0,
            {
                "daily_study_minutes": 60,
                "finish_date": "2030-11-06",
                "study_days": 4,
                "peak_daily_minutes": 60,
            },
        )

    def contradictory_proposal(self):
        proposal = self.replan_proposal(120)
        proposal["limit_change_type"] = "preference"
        proposal["reason"] = (
            "The current 60-minute limit is insufficient."
        )
        return proposal

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_different_feasible_recommendations_are_accepted(
        self,
        mock_call,
    ):
        for daily_minutes in (90, 120):
            with self.subTest(daily_minutes=daily_minutes):
                mock_call.return_value = self.response(
                    self.replan_proposal(daily_minutes)
                )

                result = propose_plan_review(**self.arguments)

                self.assertEqual(
                    result["daily_study_minutes"],
                    daily_minutes,
                )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_student_preference_and_options_are_sent(self, mock_call):
        self.arguments["preference"] = "finish_sooner"
        mock_call.return_value = self.response(
            self.replan_proposal(120)
        )

        propose_plan_review(**self.arguments)

        mock_call.assert_called_once()
        kwargs = mock_call.call_args.kwargs
        context = json.loads(kwargs["input"])

        self.assertEqual(context["preference"], "finish_sooner")
        self.assertEqual(
            context["feasible_options"],
            self.arguments["options"],
        )
        self.assertEqual(context["maximum_daily_minutes"], 120)
        self.assertEqual(context["resume_date"], "2030-11-02")
        self.assertIn(
            "You are reviewing a student's study plan.",
            kwargs["instructions"],
        )
        self.assertFalse(kwargs["parallel_tool_calls"])
        self.assertEqual(
            kwargs["tool_choice"]["name"],
            "submit_review_proposal",
        )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_unvalidated_initial_limit_is_rejected_without_retry(
        self,
        mock_call,
    ):
        mock_call.return_value = self.response(
            self.replan_proposal(105)
        )

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

        mock_call.assert_called_once()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_cannot_fit_is_accepted_without_feasible_options(
        self,
        mock_call,
    ):
        self.arguments["options"] = []
        mock_call.return_value = self.response(
            {
                "action": "cannot_fit",
                "daily_study_minutes": None,
                "limit_change_type": "not_needed",
                "reason": "No supplied option fits the remaining work.",
            }
        )

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["action"], "cannot_fit")
        mock_call.assert_called_once()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_completed_plan_can_be_kept(self, mock_call):
        self.arguments["progress"] = {
            "completed_minutes": 270,
            "pending_minutes": 0,
            "missed_minutes": 0,
            "overdue_pending_minutes": 0,
        }
        self.arguments["options"] = []
        mock_call.return_value = self.response(
            {
                "action": "keep_current_plan",
                "daily_study_minutes": None,
                "limit_change_type": "not_needed",
                "reason": "All scheduled work is completed.",
            }
        )

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["action"], "keep_current_plan")
        mock_call.assert_called_once()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_invalid_progress_is_rejected_before_api_call(
        self,
        mock_call,
    ):
        self.arguments["progress"]["missed_minutes"] = -1

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

        mock_call.assert_not_called()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_malformed_initial_json_is_rejected(self, mock_call):
        response = self.response(self.replan_proposal())
        response.output[0].arguments = "{invalid-json"
        mock_call.return_value = response

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

        mock_call.assert_called_once()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_multiple_initial_tool_calls_are_rejected(self, mock_call):
        response = self.response(self.replan_proposal())
        response.output.append(response.output[0])
        mock_call.return_value = response

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_initial_shared_client_error_is_translated(self, mock_call):
        mock_call.side_effect = AIServiceError(
            "The AI request timed out. Please try again."
        )

        with self.assertRaisesMessage(
            ProposalGenerationError,
            "The AI request timed out. Please try again.",
        ):
            propose_plan_review(**self.arguments)

        mock_call.assert_called_once()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    @patch("planner.ai.plan_review_proposal_agent.load_prompt")
    def test_prompt_failure_prevents_api_request(
        self,
        mock_load_prompt,
        mock_call,
    ):
        mock_load_prompt.side_effect = AIServiceError(
            "The AI instructions could not be loaded."
        )

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

        mock_call.assert_not_called()

    def test_tool_requires_limit_change_type(self):
        parameters = PLAN_REVIEW_PROPOSAL_TOOLS[0]["parameters"]

        self.assertIn("limit_change_type", parameters["required"])
        self.assertEqual(
            parameters["properties"]["limit_change_type"]["enum"],
            ["not_needed", "preference", "required"],
        )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_missing_initial_limit_change_type_is_rejected(
        self,
        mock_call,
    ):
        proposal = self.replan_proposal()
        del proposal["limit_change_type"]
        mock_call.return_value = self.response(proposal)

        with self.assertRaisesMessage(
            ProposalGenerationError,
            "invalid format",
        ):
            propose_plan_review(**self.arguments)

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_wrong_claim_type_is_repaired(self, mock_call):
        self.add_current_limit_option()
        first = self.replan_proposal(120)
        second = {
            **first,
            "limit_change_type": "preference",
            "reason": "The higher limit finishes two days earlier.",
        }
        mock_call.side_effect = [
            self.response(first),
            self.response(second),
        ]

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["daily_study_minutes"], 120)
        self.assertIn("2 days earlier", result["reason"])
        self.assertNotEqual(result["reason"], second["reason"])
        self.assertEqual(mock_call.call_count, 2)

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_valid_preference_increase_uses_one_request(self, mock_call):
        self.add_current_limit_option()
        proposal = self.replan_proposal(120)
        proposal["limit_change_type"] = "preference"
        mock_call.return_value = self.response(proposal)

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["daily_study_minutes"], 120)
        self.assertEqual(
            set(result),
            {"action", "daily_study_minutes", "reason"},
        )
        mock_call.assert_called_once()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_contradictory_reason_is_retried_with_feedback(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        first = self.contradictory_proposal()
        second = {
            **first,
            "reason": (
                "The current limit fits; the selected limit "
                "finishes two days earlier."
            ),
        }
        mock_call.side_effect = [
            self.response(first),
            self.response(second),
        ]

        result = propose_plan_review(**self.arguments)

        self.assertIn("60 minutes per day is feasible", result["reason"])
        self.assertIn("2 days earlier", result["reason"])
        self.assertEqual(mock_call.call_count, 2)

        retry_kwargs = mock_call.call_args_list[1].kwargs
        retry_context = json.loads(retry_kwargs["input"])
        repair = retry_context["explanation_repair"]

        self.assertIn("without claiming", repair["validation_error"])
        self.assertEqual(repair["required_daily_study_minutes"], 120)
        self.assertEqual(
            repair["required_action"],
            "replan_unfinished_work",
        )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_second_bad_explanation_uses_factual_fallback(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        mock_call.return_value = self.response(
            self.contradictory_proposal()
        )

        result = propose_plan_review(**self.arguments)

        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(result["daily_study_minutes"], 120)
        self.assertIn("60 minutes per day is feasible", result["reason"])
        self.assertIn("2030-11-06", result["reason"])
        self.assertIn("2030-11-04", result["reason"])
        self.assertIn("2 days earlier", result["reason"])
        self.assertIn("increase is optional", result["reason"])
        self.assertNotIn("insufficient", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_retry_cannot_change_validated_limit(self, mock_call):
        self.add_current_limit_option()
        second = {
            **self.replan_proposal(90),
            "limit_change_type": "preference",
        }
        mock_call.side_effect = [
            self.response(self.contradictory_proposal()),
            self.response(second),
        ]

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["daily_study_minutes"], 120)
        self.assertIn("selected 120 minutes", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_retry_network_failure_uses_fallback(self, mock_call):
        self.add_current_limit_option()
        mock_call.side_effect = [
            self.response(self.contradictory_proposal()),
            AIServiceError("The AI request timed out."),
        ]

        result = propose_plan_review(**self.arguments)

        self.assertEqual(mock_call.call_count, 2)
        self.assertEqual(result["daily_study_minutes"], 120)
        self.assertIn("increase is optional", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_malformed_retry_uses_fallback(self, mock_call):
        self.add_current_limit_option()
        malformed = self.response(self.contradictory_proposal())
        malformed.output[0].arguments = "{invalid-json"
        mock_call.side_effect = [
            self.response(self.contradictory_proposal()),
            malformed,
        ]

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["daily_study_minutes"], 120)
        self.assertIn("increase is optional", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_unsafe_retry_choice_uses_original_validated_choice(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        mock_call.side_effect = [
            self.response(self.contradictory_proposal()),
            self.response(self.replan_proposal(105)),
        ]

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["daily_study_minutes"], 120)
        self.assertEqual(mock_call.call_count, 2)

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_fallback_at_current_limit_needs_no_increase(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        proposal = {
            **self.replan_proposal(60),
            "limit_change_type": "required",
        }
        mock_call.return_value = self.response(proposal)

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["daily_study_minutes"], 60)
        self.assertIn("2030-11-06", result["reason"])
        self.assertIn("No daily-limit increase is needed", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_fallback_for_required_increase(self, mock_call):
        proposal = {
            **self.replan_proposal(120),
            "limit_change_type": "preference",
        }
        mock_call.return_value = self.response(proposal)

        result = propose_plan_review(**self.arguments)

        self.assertIn("no feasible replacement", result["reason"])
        self.assertIn("2030-11-04", result["reason"])
        self.assertIn("higher daily limit is required", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_same_finish_date_fallback_does_not_claim_days_saved(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        self.arguments["options"][2]["finish_date"] = "2030-11-06"
        mock_call.return_value = self.response(
            self.contradictory_proposal()
        )

        result = propose_plan_review(**self.arguments)

        self.assertIn("the same finish date", result["reason"])
        self.assertNotIn("days earlier", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_completed_plan_fallback_has_no_capacity_warning(
        self,
        mock_call,
    ):
        self.arguments["progress"] = {
            "completed_minutes": 270,
            "pending_minutes": 0,
            "missed_minutes": 0,
            "overdue_pending_minutes": 0,
        }
        self.arguments["options"] = []
        mock_call.return_value = self.response(
            {
                "action": "keep_current_plan",
                "daily_study_minutes": None,
                "limit_change_type": "required",
                "reason": "All work is completed.",
            }
        )

        result = propose_plan_review(**self.arguments)

        self.assertIn("No unfinished work remains", result["reason"])
        self.assertNotIn("no feasible replacement", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_cannot_fit_fallback_uses_supplied_range_and_resume_date(
        self,
        mock_call,
    ):
        self.arguments["options"] = []
        mock_call.return_value = self.response(
            {
                "action": "cannot_fit",
                "daily_study_minutes": None,
                "limit_change_type": "required",
                "reason": "No replacement fits.",
            }
        )

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["action"], "cannot_fit")
        self.assertIn("2030-11-02", result["reason"])
        self.assertIn("60 to 120 minutes", result["reason"])

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_current_limit_and_finish_comparisons_are_sent(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        proposal = self.replan_proposal(120)
        proposal["limit_change_type"] = "preference"
        mock_call.return_value = self.response(proposal)

        propose_plan_review(**self.arguments)

        context = json.loads(mock_call.call_args.kwargs["input"])
        facts = context["facts"]

        self.assertTrue(facts["current_limit_is_feasible"])
        self.assertEqual(
            facts["current_limit_finish_date"],
            "2030-11-06",
        )
        self.assertEqual(
            facts["earliest_finish_date"],
            "2030-11-04",
        )
        self.assertEqual(
            [
                option["days_earlier_than_current"]
                for option in facts["option_comparisons"]
            ],
            [0, 1, 2],
        )
        self.assertNotIn(
            "days_earlier_than_current",
            self.arguments["options"][0],
        )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_infeasible_current_limit_has_no_finish_comparison(
        self,
        mock_call,
    ):
        mock_call.return_value = self.response(self.replan_proposal())

        propose_plan_review(**self.arguments)

        context = json.loads(mock_call.call_args.kwargs["input"])
        facts = context["facts"]

        self.assertFalse(facts["current_limit_is_feasible"])
        self.assertIsNone(facts["current_limit_finish_date"])
        self.assertEqual(
            facts["earliest_finish_date"],
            "2030-11-04",
        )
        self.assertTrue(
            all(
                option["days_earlier_than_current"] is None
                for option in facts["option_comparisons"]
            )
        )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_invalid_finish_date_is_rejected_before_api_request(
        self,
        mock_call,
    ):
        self.arguments["options"][0]["finish_date"] = "invalid-date"

        with self.assertRaisesMessage(
            ProposalGenerationError,
            "invalid finish date",
        ):
            propose_plan_review(**self.arguments)

        mock_call.assert_not_called()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_unchecked_wrong_dates_in_model_prose_are_not_displayed(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        proposal = {
            **self.replan_proposal(120),
            "limit_change_type": "preference",
            "reason": (
                "The selected limit finishes on 2030-11-01, "
                "saving 99 days."
            ),
        }
        mock_call.return_value = self.response(proposal)

        result = propose_plan_review(**self.arguments)

        self.assertIn("2030-11-04", result["reason"])
        self.assertIn("2 days earlier", result["reason"])
        self.assertNotIn("2030-11-01", result["reason"])
        self.assertNotIn("99 days", result["reason"])
        mock_call.assert_called_once()

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_finish_sooner_explanation_uses_actual_improvement(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        self.arguments["preference"] = "finish_sooner"
        proposal = {
            **self.replan_proposal(120),
            "limit_change_type": "preference",
        }
        mock_call.return_value = self.response(proposal)

        result = propose_plan_review(**self.arguments)

        self.assertIn("2 days earlier", result["reason"])
        self.assertIn(
            "consistent with your preference to finish sooner",
            result["reason"],
        )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_same_day_choice_does_not_claim_finish_sooner_alignment(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        self.arguments["preference"] = "finish_sooner"
        self.arguments["options"][2]["finish_date"] = "2030-11-06"
        proposal = {
            **self.replan_proposal(120),
            "limit_change_type": "preference",
        }
        mock_call.return_value = self.response(proposal)

        result = propose_plan_review(**self.arguments)

        self.assertIn("provides no earlier finish", result["reason"])
        self.assertNotIn(
            "consistent with your preference",
            result["reason"],
        )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_lighter_workload_explanation_acknowledges_lower_limit(
        self,
        mock_call,
    ):
        self.add_current_limit_option()
        proposal = {
            **self.replan_proposal(120),
            "limit_change_type": "preference",
        }
        mock_call.return_value = self.response(proposal)

        result = propose_plan_review(**self.arguments)

        self.assertIn(
            "current-limit option also remains available "
            "with a lower daily limit",
            result["reason"],
        )
        self.assertNotIn(
            "consistent with your preference to finish sooner",
            result["reason"],
        )