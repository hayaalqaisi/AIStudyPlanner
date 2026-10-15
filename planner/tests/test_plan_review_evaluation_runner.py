import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from evaluation import run_plan_review_evaluation
from evaluation.plan_review_cases import PLAN_REVIEW_CASES
from planner.ai.plan_review_proposal_agent import ProposalGenerationError


class PlanReviewEvaluationRunnerTests(SimpleTestCase):
    def setUp(self):
        self.case = next(
            case
            for case in PLAN_REVIEW_CASES
            if case["name"] == "missed_work_finish_sooner"
        )
        self.proposal = {
            "action": "replan_unfinished_work",
            "daily_study_minutes": 120,
            "reason": "This option finishes the supplied workload sooner.",
        }

    @patch(
        "evaluation.run_plan_review_evaluation.propose_plan_review"
    )
    def test_case_records_recommendation_and_scores(self, mock_agent):
        mock_agent.return_value = self.proposal

        result = run_plan_review_evaluation.evaluate_case(
            self.case,
            repetition=1,
        )

        self.assertEqual(result["outcome"], "succeeded")
        self.assertEqual(result["proposal"], self.proposal)
        self.assertTrue(result["quality"]["proposal_valid"])
        self.assertTrue(result["quality"]["action_correct"])
        self.assertTrue(result["quality"]["preference_match"])
        self.assertEqual(result["progress"]["missed_minutes"], 60)
        self.assertEqual(result["progress"]["pending_minutes"], 180)

        mock_agent.assert_called_once()
        arguments = mock_agent.call_args.kwargs

        self.assertEqual(arguments["preference"], "finish_sooner")
        self.assertEqual(
            arguments["options"],
            result["feasible_options"],
        )

    @patch(
        "evaluation.run_plan_review_evaluation.propose_plan_review"
    )
    def test_failed_request_is_recorded(self, mock_agent):
        mock_agent.side_effect = ProposalGenerationError(
            "The AI request timed out. Please try again."
        )

        result = run_plan_review_evaluation.evaluate_case(
            self.case,
            repetition=1,
        )

        self.assertEqual(result["outcome"], "failed")
        self.assertIsNone(result["proposal"])
        self.assertIn("timed out", result["error_message"])
        self.assertFalse(result["quality"]["proposal_valid"])
        self.assertFalse(result["quality"]["action_correct"])
        self.assertFalse(result["quality"]["preference_match"])

    @patch(
        "evaluation.run_plan_review_evaluation.propose_plan_review"
    )
    def test_failed_attempts_remain_in_score_denominators(
        self,
        mock_agent,
    ):
        mock_agent.side_effect = [
            self.proposal,
            ProposalGenerationError("The AI request timed out."),
        ]

        results = [
            run_plan_review_evaluation.evaluate_case(
                self.case,
                repetition=repetition,
            )
            for repetition in (1, 2)
        ]

        summary = run_plan_review_evaluation.build_summary(results)

        self.assertEqual(summary["attempts"], 2)
        self.assertEqual(summary["successful_attempts"], 1)
        self.assertEqual(summary["failed_attempts"], 1)
        self.assertEqual(summary["accepted_proposal_rate"], 0.5)
        self.assertEqual(summary["action_accuracy_all_attempts"], 0.5)
        self.assertEqual(summary["preference_applicable_attempts"], 2)
        self.assertEqual(summary["preference_alignment"], 0.5)

    def test_runner_writes_report_in_temporary_directory(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            with (
                override_settings(
                    BASE_DIR=root,
                    OPENAI_API_KEY="test-placeholder",
                    OPENAI_MODEL="configured-test-model",
                ),
                patch(
                    "evaluation.run_plan_review_evaluation."
                    "PLAN_REVIEW_CASES",
                    [self.case],
                ),
                patch(
                    "evaluation.run_plan_review_evaluation."
                    "propose_plan_review",
                    return_value=self.proposal,
                ) as mock_agent,
                patch(
                    "evaluation.run_plan_review_evaluation.django.setup"
                ) as mock_setup,
                patch(
                    "sys.argv",
                    [
                        "run_plan_review_evaluation",
                        "--repetitions",
                        "2",
                    ],
                ),
                patch("sys.stdout", new_callable=StringIO),
            ):
                exit_code = run_plan_review_evaluation.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(mock_agent.call_count, 2)
            mock_setup.assert_called_once_with()

            reports = list(
                (root / "evaluation" / "results").glob(
                    "plan_review_evaluation_*.json"
                )
            )
            self.assertEqual(len(reports), 1)

            report = json.loads(
                reports[0].read_text(encoding="utf-8")
            )

            self.assertEqual(
                report["model"],
                "configured-test-model",
            )
            self.assertEqual(report["case_count"], 1)
            self.assertEqual(report["repetitions_per_case"], 2)
            self.assertEqual(report["summary"]["attempts"], 2)
            self.assertEqual(
                report["summary"]["preference_alignment"],
                1.0,
            )

    @override_settings(
        OPENAI_API_KEY="",
        OPENAI_MODEL="configured-test-model",
    )
    def test_missing_configuration_stops_before_ai_request(self):
        with (
            patch(
                "evaluation.run_plan_review_evaluation."
                "propose_plan_review"
            ) as mock_agent,
            patch(
                "evaluation.run_plan_review_evaluation.django.setup"
            ),
            patch(
                "sys.argv",
                ["run_plan_review_evaluation"],
            ),
            patch("sys.stderr", new_callable=StringIO),
        ):
            with self.assertRaises(SystemExit) as caught:
                run_plan_review_evaluation.main()

        self.assertEqual(caught.exception.code, 2)
        mock_agent.assert_not_called()