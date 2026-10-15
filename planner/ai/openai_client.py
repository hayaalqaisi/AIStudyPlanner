from django.conf import settings
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)


class AIServiceError(Exception):
    """An AI request failure suitable for displaying to the user."""


def call_openai(**kwargs):
    """Call the Responses API using shared application settings."""
    api_key = settings.OPENAI_API_KEY
    model = settings.OPENAI_MODEL

    if not api_key or not model:
        raise AIServiceError(
            "OpenAI configuration is missing. "
            "Check OPENAI_API_KEY and OPENAI_MODEL."
        )

    if "model" in kwargs:
        raise AIServiceError(
            "The OpenAI model must be configured through Django settings."
        )

    request_options = {
        **kwargs,
        "model": model,
        "store": False,
    }

    try:
        with OpenAI(
            api_key=api_key,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=settings.OPENAI_MAX_RETRIES,
        ) as client:
            return client.responses.create(**request_options)

    except AuthenticationError:
        raise AIServiceError(
            "OpenAI authentication failed. Check your API key."
        ) from None

    except RateLimitError:
        raise AIServiceError(
            "OpenAI could not accept the request. "
            "Check API quota, billing, and rate limits."
        ) from None

    except APITimeoutError:
        raise AIServiceError(
            "The AI request timed out. Please try again."
        ) from None

    except APIConnectionError:
        raise AIServiceError(
            "Could not connect to OpenAI. Check your internet connection."
        ) from None

    except APIStatusError:
        raise AIServiceError(
            "OpenAI could not complete the request. "
            "Check model access or try again later."
        ) from None