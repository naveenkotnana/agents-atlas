"""app/schemas/echo.py
Pydantic v2 schemas for the Echo Check endpoint.

These schemas define the DATA CONTRACT — what the client must send and
what they will receive back. Pydantic validates every field BEFORE your
Python handler function executes.

Key design decisions:
  - model_config forbid = "forbid"  →  rejects unexpected fields (security)
  - Field(min_length=..., max_length=...)  →  prevents empty or oversized input
  - Literal[...]  →  restricts department to an exact allowlist (enum-like)
  - Field(ge=..., le=...)  →  constrains priority to a bounded integer range
"""
from typing import Literal

from pydantic import BaseModel, Field


class EchoCheckRequest(BaseModel):
    """
    Inbound payload for POST /api/v1/echo-check.

    Validation rules (enforced by Pydantic BEFORE handler code runs):
      - query:      string, 3-200 chars, whitespace stripped
      - department: must be exactly one of the four allowed values
      - priority:   integer, 1 through 5 inclusive
    """

    query: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="The user's enterprise query. 3-200 characters.",
        examples=["Explain hybrid retrieval"],
    )

    department: Literal["Engineering", "Sales", "Legal", "Executive"] = Field(
        ...,
        description="Business department submitting the query.",
        examples=["Engineering"],
    )

    priority: int = Field(
        ...,
        ge=1,
        le=5,
        description="Query priority level. 1 (lowest) to 5 (critical).",
        examples=[3],
    )

    model_config = {
        "extra": "forbid",  # Reject any field not defined above
        "json_schema_extra": {
            "examples": [
                {
                    "query": "Explain hybrid retrieval",
                    "department": "Engineering",
                    "priority": 3,
                }
            ]
        },
    }


class EchoCheckResponse(BaseModel):
    """
    Outbound payload returned on successful validation + business checks.
    """

    query: str = Field(..., description="The validated, whitespace-stripped query.")
    status: str = Field(
        default="accepted",
        description="Processing status of the echo check.",
    )
    request_id: str = Field(
        ...,
        description="Correlation ID assigned by the RequestCorrelationMiddleware.",
    )
