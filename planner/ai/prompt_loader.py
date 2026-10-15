from pathlib import Path

from planner.ai.openai_client import AIServiceError


PROMPTS_DIRECTORY = Path(__file__).resolve().parent / "prompts"


def load_prompt(filename):
    """Read an application-owned prompt as UTF-8 text."""
    try:
        prompt = (PROMPTS_DIRECTORY / filename).read_text(
            encoding="utf-8",
        ).strip()
    except (OSError, UnicodeError):
        raise AIServiceError(
            "The AI instructions could not be loaded. "
            "Check the application's prompt files."
        ) from None

    if not prompt:
        raise AIServiceError(
            "The AI instructions file is empty."
        )

    return prompt