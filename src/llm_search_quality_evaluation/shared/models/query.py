from __future__ import annotations
from typing import Dict, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict

# Runtime provenance used for per-run budgeting, not persisted data. Cache loads default
# to "cached" until promoted by a fresh add in the current run.
QuerySource = Literal["user", "category", "llm", "cached"]

# Lower values are higher priority. User/category reflect explicit intent, followed by
# generated queries and cached queries.
SOURCE_PRIORITY: Dict[str, int] = {
    "user": 0,
    "category": 0,
    "llm": 1,
    "cached": 2,
}


class Query(BaseModel):
    """Represents a search query."""

    model_config = ConfigDict(extra='ignore')

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique identifier of the query.", min_length=1)
    text: str = Field(..., description="The raw query text.", min_length=1)
    # Excluded from serialization so datastore cache loads default to "cached".
    source: QuerySource = Field(default="cached", exclude=True)
