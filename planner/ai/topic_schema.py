"""Expected JSON structure for AI topic extraction."""


TOPIC_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                },
                "required": ["title", "description"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["topics"],
    "additionalProperties": False,
}