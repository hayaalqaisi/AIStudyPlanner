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
                "limit_change_type": {
                    "type": "string",
                    "enum": [
                        "not_needed",
                        "preference",
                        "required",
                    ],
                    "description": (
                        "Use not_needed when no daily-limit increase "
                        "is proposed, including keep_current_plan and "
                        "cannot_fit. Use preference for an increase "
                        "when the current limit is feasible. Use required "
                        "for an increase when the current limit is not "
                        "feasible and a higher feasible limit is selected."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": (
                        "Briefly explain the recommendation using "
                        "the supplied facts and student preference. "
                        "The explanation must agree with "
                        "limit_change_type and the scheduling facts."
                    ),
                },
            },
            "required": [
                "action",
                "daily_study_minutes",
                "limit_change_type",
                "reason",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
]