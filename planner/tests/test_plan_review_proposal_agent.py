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

    def configure_response(self, mock_call, proposal):
        mock_call.return_value = SimpleNamespace(
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
            "reason": "A feasible workload recommendation.",
        }

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_different_feasible_recommendations_are_accepted(
        self,
        mock_call,
    ):
        for daily_minutes in (90, 120):
            with self.subTest(daily_minutes=daily_minutes):
                self.configure_response(
                    mock_call,
                    self.replan_proposal(daily_minutes),
                )

                result = propose_plan_review(**self.arguments)

                self.assertEqual(
                    result["daily_study_minutes"],
                    daily_minutes,
                )

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_student_preference_and_options_are_sent(self, mock_call):
        self.arguments["preference"] = "finish_sooner"
        self.configure_response(mock_call, self.replan_proposal(120))

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
    def test_unvalidated_daily_limit_is_rejected(self, mock_call):
        self.configure_response(mock_call, self.replan_proposal(105))

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_cannot_fit_is_accepted_without_feasible_options(
        self,
        mock_call,
    ):
        self.arguments["options"] = []
        self.configure_response(
            mock_call,
            {
                "action": "cannot_fit",
                "daily_study_minutes": None,
                "reason": "No supplied option fits the remaining work.",
            },
        )

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["action"], "cannot_fit")

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_completed_plan_can_be_kept(self, mock_call):
        self.arguments["progress"] = {
            "completed_minutes": 270,
            "pending_minutes": 0,
            "missed_minutes": 0,
            "overdue_pending_minutes": 0,
        }
        self.arguments["options"] = []

        self.configure_response(
            mock_call,
            {
                "action": "keep_current_plan",
                "daily_study_minutes": None,
                "reason": "All scheduled work is completed.",
            },
        )

        result = propose_plan_review(**self.arguments)

        self.assertEqual(result["action"], "keep_current_plan")

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
    def test_malformed_json_is_rejected(self, mock_call):
        self.configure_response(mock_call, self.replan_proposal())
        mock_call.return_value.output[0].arguments = "{invalid-json"

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_multiple_tool_calls_are_rejected(self, mock_call):
        self.configure_response(mock_call, self.replan_proposal())
        response = mock_call.return_value
        response.output.append(response.output[0])

        with self.assertRaises(ProposalGenerationError):
            propose_plan_review(**self.arguments)

    @patch("planner.ai.plan_review_proposal_agent.call_openai")
    def test_shared_client_error_is_translated(self, mock_call):
        mock_call.side_effect = AIServiceError(
            "The AI request timed out. Please try again."
        )

        with self.assertRaisesMessage(
            ProposalGenerationError,
            "The AI request timed out. Please try again.",
        ):
            propose_plan_review(**self.arguments)

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