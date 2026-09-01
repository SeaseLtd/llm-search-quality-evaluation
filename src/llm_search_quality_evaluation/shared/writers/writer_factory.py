from llm_search_quality_evaluation.shared.writers.abstract_writer import AbstractWriter
from llm_search_quality_evaluation.shared.writers.evaluation_dataset_writer import EvaluationDatasetWriter
from llm_search_quality_evaluation.shared.writers.mteb_writer import MtebWriter
from llm_search_quality_evaluation.shared.writers.quepid_writer import QuepidWriter
from llm_search_quality_evaluation.shared.writers.rre_writer import RreWriter
from llm_search_quality_evaluation.shared.writers.writer_config import WriterConfig
from llm_search_quality_evaluation.shared.models.output_format import OutputFormat

from typing import Mapping, Type, TypeAlias
import logging

log = logging.getLogger(__name__)

WriterType: TypeAlias = Type[AbstractWriter]

class WriterFactory:
    OUTPUT_FORMAT_REGISTRY: Mapping[OutputFormat, WriterType] = {
        OutputFormat.QUEPID: QuepidWriter,
        OutputFormat.RRE: RreWriter,
        OutputFormat.MTEB: MtebWriter,
        OutputFormat.EVALUATION_DATASET: EvaluationDatasetWriter,
    }

    @classmethod
    def build(cls, writer_config: WriterConfig) -> AbstractWriter:
        output_format: OutputFormat = writer_config.output_format
        log.info(f"Selected output format: {output_format}")
        return cls.OUTPUT_FORMAT_REGISTRY[output_format](writer_config)
