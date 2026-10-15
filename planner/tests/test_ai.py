import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from planner.ai.openai_client import AIServiceError
from planner.ai.topic_extractor import (
    TopicExtractionError,
    extract_topics,
)
from planner.ai.topic_schema import TOPIC_EXTRACTION_SCHEMA


class TopicExtractionTests(SimpleTestCase):
    def configure_response(self, mock_call, topics):
        mock_call.return_value = SimpleNamespace(
            status="completed",
            output_text=json.dumps({"topics": topics}),
        )

    @patch("planner.ai.topic_extractor.call_openai")
    def test_valid_topics_are_accepted(self, mock_call):
        topics = [
            {
                "title": "SQL queries",
                "description": "SELECT statements and filtering.",
            },
        ]
        self.configure_response(mock_call, topics)

        result = extract_topics("Study topics: SQL queries.")

        self.assertEqual(result, topics)
        mock_call.assert_called_once()

        kwargs = mock_call.call_args.kwargs

        self.assertEqual(
            kwargs["input"],
            "Study topics: SQL queries.",
        )
        self.assertIn(
            "Extract the main study topics",
            kwargs["instructions"],
        )
        self.assertEqual(
            kwargs["text"]["format"]["schema"],
            TOPIC_EXTRACTION_SCHEMA,
        )
        self.assertTrue(kwargs["text"]["format"]["strict"])
        self.assertEqual(kwargs["max_output_tokens"], 6000)

    @patch("planner.ai.topic_extractor.call_openai")
    def test_duplicate_titles_are_rejected(self, mock_call):
        self.configure_response(
            mock_call,
            [
                {"title": "SQL queries", "description": ""},
                {"title": "  SQL   QUERIES  ", "description": ""},
            ],
        )

        with self.assertRaises(TopicExtractionError):
            extract_topics("Study topics: SQL queries.")

    @patch("planner.ai.topic_extractor.call_openai")
    def test_extra_topic_fields_are_rejected(self, mock_call):
        self.configure_response(
            mock_call,
            [
                {
                    "title": "SQL queries",
                    "description": "",
                    "unexpected_field": "Not allowed",
                },
            ],
        )

        with self.assertRaises(TopicExtractionError):
            extract_topics("Study topics: SQL queries.")

    @patch("planner.ai.topic_extractor.call_openai")
    def test_shared_client_error_is_translated(self, mock_call):
        mock_call.side_effect = AIServiceError(
            "The AI request timed out. Please try again."
        )

        with self.assertRaisesMessage(
            TopicExtractionError,
            "The AI request timed out. Please try again.",
        ):
            extract_topics("Study topics: SQL queries.")

    @patch("planner.ai.topic_extractor.call_openai")
    @patch("planner.ai.topic_extractor.load_prompt")
    def test_prompt_failure_prevents_api_request(
        self,
        mock_load_prompt,
        mock_call,
    ):
        mock_load_prompt.side_effect = AIServiceError(
            "The AI instructions could not be loaded."
        )

        with self.assertRaises(TopicExtractionError):
            extract_topics("Study topics: SQL queries.")

        mock_call.assert_not_called()