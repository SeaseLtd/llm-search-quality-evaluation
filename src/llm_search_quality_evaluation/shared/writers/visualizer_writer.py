import gzip
import json
import logging
from pathlib import Path

from llm_search_quality_evaluation.shared.models.visualizer_format import Visualizer
from llm_search_quality_evaluation.shared.writers.abstract_writer import AbstractWriter
from llm_search_quality_evaluation.shared.data_store import DataStore

log = logging.getLogger(__name__)

OUTPUT_FILENAME = "visualizer.json.gz"

class VisualizerWriter(AbstractWriter):
    """
    VisualizerWriter: Write the data structure to a format readable by the DatasetGenerator Visualizer.
    """

    def write(self, output_path: str | Path, datastore: DataStore) -> None:
        """Writes queries, documents, and their ratings to a compressed json file."""
        output_path = Path(output_path) / OUTPUT_FILENAME
        output_path.parent.mkdir(parents=True, exist_ok=True)

        visualizer: Visualizer = Visualizer(
            queries=datastore.get_queries(),
            documents=datastore.get_documents(),
            ratings=datastore.get_ratings(),
            max_rating_value=max((rating.score for rating in datastore.get_ratings()), default=1)  # TODO: get this value from the config file
        )

        with gzip.open(output_path, 'wt', encoding='utf-8') as json_file:
            json.dump(visualizer.model_dump(mode='json'), json_file)
            log.info(f"Visualizer formatted records have been written to the compressed json file, {str(output_path)}")

