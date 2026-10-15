"""Tool definition for proposing a study-plan review outcome."""


PLAN_REVIEW_PROPOSAL_TOOLS = [
    {
        "type": "function",
        "name": "submit_review_proposal",
        "description": (
            "Recommend keeping the current plan, rescheduling unfinished "
            "work using one of the supplied feasible daily limits, or "
            "reporting that no feasible option exists. Consider the "
            "student's workload preference and the supplied finish dates. "
            "This submits a proposal only; it does not modify the plan."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "keep_current_plan",
                        "replan_unfinished_work",
                        "cannot_fit",
                    ],
                    "description": "The recommended review outcome.",
                },
                "daily_study_minutes": {
                    "type": ["integer", "null"],
                    "description": (
                        "For replanning, choose a daily_study_minutes "
                        "value from the supplied feasible options. "
                        "For keep_current_plan or cannot_fit, use null."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Explain the recommendation using the student's "
                        "preference, progress, and supplied scheduling "
                        "options. Describe the workload and finish-date "
                        "tradeoff without inventing facts."
                    ),
                },
            },
            "required": [
                "action",
                "daily_study_minutes",
                "reason",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
]