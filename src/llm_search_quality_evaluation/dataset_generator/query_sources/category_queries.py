from __future__ import annotations

from logging import Logger, getLogger
from typing import List, Optional

from llm_search_quality_evaluation.dataset_generator.config import Config
from llm_search_quality_evaluation.shared.data_store import DataStore
from llm_search_quality_evaluation.shared.search_engines import BaseSearchEngine

log: Logger = getLogger(__name__)


def add_category_queries(config: Config, data_store: DataStore,
                         search_engine: BaseSearchEngine) -> None:
    """Render and store category queries from explicit or engine-discovered values.

    With a text template, each value replaces the engine-specific placeholder.
    """
    if not config.category_queries:
        return
    placeholder = config.category_query_placeholder
    for source in config.category_queries:
        if source.values is not None:
            values: List[str] = list(source.values)
        else:
            # Config validation guarantees exactly one of values / values_query_template_file
            # is set, so in this branch the template file is present.
            assert source.values_query_template_file is not None
            values = search_engine.fetch_field_values(
                source.values_query_template_file, source.field
            )

        if not values:
            log.warning(
                f"[add_category_queries] no values for field='{source.field}' "
                f"(template={source.values_query_template_file}); skipping this source"
            )
            continue

        template: Optional[str] = (
            source.query_text_template_file.read_text(encoding="utf-8").strip()
            if source.query_text_template_file is not None
            else None
        )
        for value in values:
            query_text = value if template is None else template.replace(placeholder, value)
            data_store.add_query(query_text, source="category")
            log.debug(f"[add_category_queries] added query='{query_text}'")
