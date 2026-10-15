import json

from planner.ai.openai_client import AIServiceError, call_openai
from planner.ai.prompt_loader import load_prompt
from planner.ai.topic_schema import TOPIC_EXTRACTION_SCHEMA


MAX_INPUT_CHARACTERS = 100_000
MAX_TOPICS = 50


class TopicExtractionError(Exception):
    """A topic-extraction problem suitable for displaying to the user."""


def extract_topics(syllabus_text):
    """Return validated topic dictionaries without accessing the database."""
    if not isinstance(syllabus_text, str) or not syllabus_text.strip():
        raise TopicExtractionError("The syllabus must contain text.")

    if len(syllabus_text) > MAX_INPUT_CHARACTERS:
        raise TopicExtractionError(
            "The syllabus contains too much text for topic extraction."
        )

    try:
        instructions = load_prompt("topic_extraction.md")

        response = call_openai(
            instructions=instructions,
            input=syllabus_text,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "syllabus_topics",
                    "schema": TOPIC_EXTRACTION_SCHEMA,
                    "strict": True,
                },
            },
            max_output_tokens=6000,
        )
    except AIServiceError as error:
        raise TopicExtractionError(str(error)) from None

    if response.status != "completed" or not response.output_text:
        raise TopicExtractionError(
            "OpenAI did not return a complete topic list."
        )

    try:
        data = json.loads(response.output_text)
    except json.JSONDecodeError:
        raise TopicExtractionError(
            "OpenAI returned an unreadable topic list."
        ) from None

    return _validate_topics(data)


def _validate_topics(data):
    """Check returned data before it can be used by a database service."""
    if not isinstance(data, dict) or set(data) != {"topics"}:
        raise TopicExtractionError(
            "The topic response has an invalid format."
        )

    topics = data["topics"]

    if not isinstance(topics, list) or len(topics) > MAX_TOPICS:
        raise TopicExtractionError(
            "The topic list has an invalid size."
        )

    if not topics:
        raise TopicExtractionError(
            "No study topics were found in this syllabus."
        )

    validated_topics = []
    seen_titles = set()

    for topic in topics:
        if not isinstance(topic, dict) or set(topic) != {
            "title",
            "description",
        }:
            raise TopicExtractionError(
                "A topic has an invalid format."
            )

        title = topic["title"]
        description = topic["description"]

        if not isinstance(title, str) or not isinstance(description, str):
            raise TopicExtractionError(
                "Topic fields must contain text."
            )

        title = title.strip()
        description = description.strip()

        if not title or len(title) > 200 or len(description) > 1000:
            raise TopicExtractionError(
                "A topic contains an empty title or oversized text."
            )

        normalized_title = " ".join(title.split()).casefold()

        if normalized_title in seen_titles:
            raise TopicExtractionError(
                "The extracted list contains duplicate topic titles."
            )

        seen_titles.add(normalized_title)
        validated_topics.append(
            {
                "title": title,
                "description": description,
            }
        )

    return validated_topics