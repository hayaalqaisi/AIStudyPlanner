import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from evaluation import run_topic_evaluation
from planner.ai.topic_extractor import TopicExtractionError


class TopicEvaluationRunnerTests(SimpleTestCase):
    def setUp(self):
        self.case = {
            "name": "test_case",
            "syllabus_text": "Study topics: SQL queries.",
            "expected_titles": ["SQL queries"],
        }

    def test_runner_writes_report_using_django_settings(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            with (
                override_settings(
                    BASE_DIR=root,
                    OPENAI_API_KEY="test-placeholder",
                    OPENAI_MODEL="configured-test-model",
                ),
                patch(
                    "evaluation.run_topic_evaluation."
                    "TOPIC_EXTRACTION_CASES",
                    [self.case],
                ),
                patch(
                    "evaluation.run_topic_evaluation.extract_topics",
                    return_value=[
                        {
                            "title": "SQL queries",
                            "description": "",
                        },
                    ],
                ) as mock_extract,
                patch(
                    "evaluation.run_topic_evaluation.django.setup"
                ) as mock_setup,
                patch(
                    "sys.argv",
                    [
                        "run_topic_evaluation",
                        "--repetitions",
                        "2",
                    ],
                ),
                patch("sys.stdout", new_callable=StringIO),
            ):
                exit_code = run_topic_evaluation.main()

            self.assertEqual(exit_code, 0)
            mock_setup.assert_called_once_with()
            self.assertEqual(mock_extract.call_count, 2)

            reports = list(
                (root / "evaluation" / "results").glob("*.json")
            )
            self.assertEqual(len(reports), 1)

            report = json.loads(
                reports[0].read_text(encoding="utf-8")
            )

            self.assertEqual(
                report["model"],
                "configured-test-model",
            )
            self.assertEqual(report["repetitions_per_case"], 2)
            self.assertEqual(report["summary"]["attempts"], 2)
            self.assertEqual(
                report["summary"]["successful_attempts"],
                2,
            )
            self.assertEqual(report["summary"]["micro_f1"], 1.0)

    @patch("evaluation.run_topic_evaluation.extract_topics")
    def test_failed_extraction_is_recorded(self, mock_extract):
        mock_extract.side_effect = TopicExtractionError(
            "The AI request timed out. Please try again."
        )

        result = run_topic_evaluation.evaluate_case(
            self.case,
            repetition=1,
        )

        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["predicted_titles"], [])
        self.assertIn("timed out", result["error_message"])
        self.assertEqual(result["quality"]["false_negatives"], 1)
        self.assertEqual(result["quality"]["f1"], 0.0)

    @override_settings(
        OPENAI_API_KEY="",
        OPENAI_MODEL="configured-test-model",
    )
    def test_missing_configuration_stops_before_extraction(self):
        with (
            patch(
                "evaluation.run_topic_evaluation.extract_topics"
            ) as mock_extract,
            patch(
                "evaluation.run_topic_evaluation.django.setup"
            ),
            patch(
                "sys.argv",
                ["run_topic_evaluation", "--repetitions", "1"],
            ),
            patch("sys.stderr", new_callable=StringIO),
        ):
            with self.assertRaises(SystemExit) as caught:
                run_topic_evaluation.main()

        self.assertEqual(caught.exception.code, 2)
        mock_extract.assert_not_called()