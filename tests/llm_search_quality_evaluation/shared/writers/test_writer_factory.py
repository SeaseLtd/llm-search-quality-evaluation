from llm_search_quality_evaluation.shared.models import OutputFormat
from llm_search_quality_evaluation.shared.writers.writer_factory import WriterFactory


def test_every_output_format_has_a_writer():
    assert set(OutputFormat) == set(WriterFactory.OUTPUT_FORMAT_REGISTRY)
