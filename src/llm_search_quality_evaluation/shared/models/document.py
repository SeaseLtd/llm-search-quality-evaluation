from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import logging
from llm_search_quality_evaluation.shared.utils import is_json_serializable

log = logging.getLogger(__name__)

class Document(BaseModel):
    """Represents a document with a unique identifier and fields."""

    model_config = ConfigDict(extra='ignore')

    id: str = Field(
        ...,
        description="Unique identifier of the document.",
        min_length=1
    )
    fields: Dict[str, Any] = Field(
        ...,
        description="Fields of the document."
    )
    is_used_to_generate_queries: bool = Field(default=False,
                                                description="Whether the document is used to generate queries.")

    @field_validator('fields')
    @classmethod
    def validate_fields(cls, field_values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate field keys and values; empty dicts are allowed for id-only retrieval."""
        if any(not key for key in field_values.keys()):
            raise ValueError('Field keys cannot be empty strings.')

        if not is_json_serializable(field_values):
            raise ValueError('Field values must be JSON-serializable (primitives, lists, or dicts).')
        return field_values
