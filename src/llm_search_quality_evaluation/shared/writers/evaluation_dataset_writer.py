import gzip
import json
import logging
from pathlib import Path

from llm_search_quality_evaluation.shared.data_store import DataStore
from llm_search_quality_evaluation.shared.models.evaluation_dataset_format import EvaluationDataset
from llm_search_quality_evaluation.shared.writers.abstract_writer import AbstractWriter

log = logging.getLogger(__name__)

OUTPUT_FILENAME = "evaluation_dataset.json.gz"


class EvaluationDatasetWriter(AbstractWriter):
    """
    Writes the DataStore to a self-contained evaluation dataset file
    (evaluation_dataset.json.gz), readable by the dataset-generator Visualizer
    and usable as input for the approximate vector search evaluation.
    """

    def write(self, output_path: str | Path, datastore: DataStore) -> None:
        """Writes queries, documents and their ratings to a compressed json file."""
        output_path = Path(output_path) / OUTPUT_FILENAME
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ratings = datastore.get_ratings()
        evaluation_dataset = EvaluationDataset(
            queries=datastore.get_queries(),
            documents=datastore.get_documents(),
            ratings=ratings,
            max_rating_value=max((rating.score for rating in ratings), default=1),
        )

        with gzip.open(output_path, "wt", encoding="utf-8") as json_file:
            json.dump(evaluation_dataset.model_dump(mode="json"), json_file)
        log.info(
            "Evaluation dataset has been written to the compressed json file, "
            f"{str(output_path)}"
        )
