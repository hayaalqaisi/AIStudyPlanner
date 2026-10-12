"""Tool definitions available to the study-plan review agent."""


PLAN_REVIEW_TOOLS = [
    {
        "type": "function",
        "name": "keep_current_plan",
        "description": (
            "Keep the current study plan when its progress does not "
            "require rescheduling."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": (
                        "A brief explanation based on the supplied "
                        "session progress."
                    ),
                },
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "replan_unfinished_work",
        "description": (
            "Request rescheduling of unfinished work when missed "
            "or overdue sessions require an updated plan. "
            "The server checks capacity and exam deadlines."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": (
                        "A brief explanation of why the supplied "
                        "session progress requires replanning."
                    ),
                },
            },
            "required": ["reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]