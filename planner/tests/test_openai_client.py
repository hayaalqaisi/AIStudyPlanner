from unittest.mock import patch

import httpx2
from django.test import SimpleTestCase, override_settings
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from planner.ai.openai_client import AIServiceError, call_openai


@override_settings(
    OPENAI_API_KEY="test-placeholder",
    OPENAI_MODEL="test-model",
    OPENAI_TIMEOUT_SECONDS=60.0,
    OPENAI_MAX_RETRIES=0,
)
class OpenAIClientTests(SimpleTestCase):
    @patch("planner.ai.openai_client.OpenAI")
    def test_request_uses_shared_settings(self, mock_openai):
        client = mock_openai.return_value.__enter__.return_value
        expected_response = object()
        client.responses.create.return_value = expected_response

        result = call_openai(
            input="Test input",
            instructions="Test instructions",
            max_output_tokens=100,
        )

        self.assertIs(result, expected_response)

        mock_openai.assert_called_once_with(
            api_key="test-placeholder",
            timeout=60.0,
            max_retries=0,
        )
        client.responses.create.assert_called_once_with(
            input="Test input",
            instructions="Test instructions",
            max_output_tokens=100,
            model="test-model",
            store=False,
        )
        mock_openai.return_value.__exit__.assert_called_once()

    @patch("planner.ai.openai_client.OpenAI")
    def test_response_storage_is_always_disabled(self, mock_openai):
        client = mock_openai.return_value.__enter__.return_value

        call_openai(input="Test input", store=True)

        self.assertFalse(
            client.responses.create.call_args.kwargs["store"]
        )

    @patch("planner.ai.openai_client.OpenAI")
    def test_missing_configuration_is_rejected(self, mock_openai):
        for configuration in (
            {"OPENAI_API_KEY": ""},
            {"OPENAI_MODEL": ""},
        ):
            with self.subTest(configuration=configuration):
                with override_settings(**configuration):
                    with self.assertRaises(AIServiceError):
                        call_openai(input="Test input")

        mock_openai.assert_not_called()

    @patch("planner.ai.openai_client.OpenAI")
    def test_per_request_model_override_is_rejected(self, mock_openai):
        with self.assertRaises(AIServiceError):
            call_openai(
                input="Test input",
                model="another-model",
            )

        mock_openai.assert_not_called()

    @patch("planner.ai.openai_client.OpenAI")
    def test_sdk_errors_become_safe_application_errors(
        self,
        mock_openai,
    ):
        request = httpx2.Request(
            "POST",
            "https://api.openai.com/v1/responses",
        )

        errors = [
            (
                AuthenticationError(
                    "Internal authentication details",
                    response=httpx2.Response(401, request=request),
                    body=None,
                ),
                "OpenAI authentication failed.",
            ),
            (
                RateLimitError(
                    "Internal quota details",
                    response=httpx2.Response(429, request=request),
                    body=None,
                ),
                "OpenAI could not accept the request.",
            ),
            (
                APITimeoutError(request=request),
                "The AI request timed out.",
            ),
            (
                APIConnectionError(request=request),
                "Could not connect to OpenAI.",
            ),
            (
                APIStatusError(
                    "Internal service details",
                    response=httpx2.Response(500, request=request),
                    body=None,
                ),
                "OpenAI could not complete the request.",
            ),
        ]

        client = mock_openai.return_value.__enter__.return_value

        for sdk_error, expected_message in errors:
            with self.subTest(error=type(sdk_error).__name__):
                client.responses.create.side_effect = sdk_error

                with self.assertRaises(AIServiceError) as caught:
                    call_openai(input="Test input")

                self.assertIn(expected_message, str(caught.exception))
                self.assertNotIn(
                    "Internal",
                    str(caught.exception),
                )