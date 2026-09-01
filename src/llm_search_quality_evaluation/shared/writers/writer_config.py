from typing import Optional
import logging

from pydantic import BaseModel, Field
from llm_search_quality_evaluation.shared.models.output_format import OutputFormat

log = logging.getLogger(__name__)

class WriterConfig(BaseModel):
    output_format: OutputFormat
    index: str = Field(..., description="Name of the index/collection of the search engine")
    id_field: Optional[str] = Field(None, description="ID field for the unique key.")
    query_template: Optional[str] = Field(None, description="Query template for rre evaluator.")
    query_placeholder: Optional[str] = Field(None,
                                                 description="Key-value pair to substitute in the rre query template.")
