from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Literal
from urllib.parse import urljoin

import yaml
from pydantic import BaseModel, Field, FilePath, HttpUrl, field_validator, model_validator

from llm_search_quality_evaluation.vector_search_doctor.approximate_search_evaluator.evaluation.metrics import (
    DEFAULT_METRICS,
    is_supported_metric,
)

log = logging.getLogger(__name__)


class Config(BaseModel):
    query_template: FilePath = Field(
        ...,
        description="Path to a query template file with a placeholder for keywords.",
    )
    search_engine_type: Literal["solr", "elasticsearch", "opensearch", "datafari"]
    collection_name: str = Field(..., description="Name of the index/collection.")
    search_engine_url: HttpUrl = Field(..., description="Base search engine URL.")
    id_field: Optional[str] = Field(None, description="ID field for the unique key.")
    query_placeholder: str = Field(
        default="$query",
        description="Placeholder substituted with the keyword in the query template.",
    )
    evaluation_dataset_path: FilePath = Field(
        ...,
        description="Path to the evaluation_dataset.json.gz file.",
    )
    embeddings_file: Optional[FilePath] = Field(
        None,
        description="Path to the precomputed query embeddings JSONL file. Required for vector queries.",
    )
    output_destination: Path = Field(
        Path("resources"),
        description="Directory where evaluation results are written.",
    )
    doc_fields: list[str] = Field(
        default_factory=list,
        description="Document fields to request from the engine.",
    )
    top_k: int = Field(
        default=10,
        gt=0,
        description="Number of top results per query fed to the metrics.",
    )
    metrics: list[str] = Field(
        default_factory=lambda: list(DEFAULT_METRICS),
        description="ranx metric names to compute (e.g. ndcg@10, map@10).",
    )

    @property
    def search_engine_collection_endpoint(self) -> HttpUrl:
        """Return the endpoint used by the search engine."""
        if self.search_engine_type == "datafari":
            return self.search_engine_url

        return HttpUrl(
            urljoin(
                self.search_engine_url.encoded_string() + "/",
                self.collection_name + "/"
            )
        )

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("metrics must not be empty")
        unsupported = [m for m in value if not is_supported_metric(m)]
        if unsupported:
            raise ValueError(f"Unsupported metric(s): {unsupported}")
        return value

    @model_validator(mode="after")
    def adjust_id_field(self) -> "Config":
        if self.id_field is None:
            if self.search_engine_type == "elasticsearch":
                self.id_field = "_id"
            else:  # solr, opensearch
                self.id_field = "id"
        return self

    @classmethod
    def load(cls, config_path: str) -> "Config":
        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)
            log.debug("Approximate Search Evaluator configuration file loaded successfully.")
        return cls(**raw_config)
