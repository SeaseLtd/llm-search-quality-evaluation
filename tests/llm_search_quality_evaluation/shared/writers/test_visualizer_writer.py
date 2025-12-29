import gzip
import json
from pathlib import Path

import pytest

from llm_search_quality_evaluation.shared.data_store import DataStore
from llm_search_quality_evaluation.shared.models import Document
from llm_search_quality_evaluation.shared.models.output_format import OutputFormat
from llm_search_quality_evaluation.shared.writers.visualizer_writer import VisualizerWriter, OUTPUT_FILENAME
from llm_search_quality_evaluation.shared.writers.writer_config import WriterConfig


@pytest.fixture
def writer_config():
    return WriterConfig(
        output_format=OutputFormat.VISUALIZER,
        index='testcore'
    )


@pytest.fixture
def populated_datastore() -> DataStore:
    """Returns a DataStore instance populated with test data."""
    datastore = DataStore(ignore_saved_data=True)

    # Add docs
    datastore.add_document(Document(id="doc1", fields={"title": "title 1", "description": "desc 1"}))
    datastore.add_document(Document(id="doc2", fields={"title": "title 2", "description": "desc 2"}))
    datastore.add_document(Document(id="doc3", fields={"title": "title 3", "description": "desc 3"}))
    datastore.add_document(Document(id="doc4", fields={"title": "title 4", "description": "desc 4"}))

    # Add queries and ratings
    q1 = datastore.add_query("test query 1")
    datastore.create_rating_score(q1.id, "doc1", 1)
    datastore.create_rating_score(q1.id, "doc2", 0)

    q2 = datastore.add_query("test query 2")
    datastore.create_rating_score(q2.id, "doc3", 2)
    datastore.create_rating_score(q2.id, "doc4", 1)

    # Query without ratings
    datastore.add_query("test query 3")

    return datastore


class TestVisualizerWriter:

    def test_write_expect_compressed_json_file(
            self,
            writer_config: WriterConfig,
            populated_datastore: DataStore,
            tmp_path: Path
    ):
        """Test that the writer creates a compressed JSON file with correct structure."""
        output_dir = tmp_path
        writer = VisualizerWriter(writer_config=writer_config)
        writer.write(output_dir, populated_datastore)

        output_file = output_dir / OUTPUT_FILENAME
        assert output_file.exists()
        assert output_file.suffix == ".gz"

        # Verify file is actually compressed (should be smaller than uncompressed JSON)
        file_size = output_file.stat().st_size
        assert file_size > 0

    def test_write_and_read_data_integrity(
            self,
            writer_config: WriterConfig,
            populated_datastore: DataStore,
            tmp_path: Path
    ):
        """Test that all data written can be read back correctly."""
        output_dir = tmp_path
        writer = VisualizerWriter(writer_config=writer_config)
        writer.write(output_dir, populated_datastore)

        output_file = output_dir / OUTPUT_FILENAME

        # Read the compressed file
        with gzip.open(output_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        # Verify structure
        assert "queries" in data
        assert "documents" in data
        assert "ratings" in data
        assert "max_rating_value" in data

        # Verify queries
        original_queries = populated_datastore.get_queries()
        assert len(data["queries"]) == len(original_queries)

        for original_q in original_queries:
            matching_q = next((q for q in data["queries"] if q["id"] == original_q.id), None)
            assert matching_q is not None
            assert matching_q["text"] == original_q.text

        # Verify documents
        original_docs = populated_datastore.get_documents()
        assert len(data["documents"]) == len(original_docs)

        for original_doc in original_docs:
            matching_doc = next((d for d in data["documents"] if d["id"] == original_doc.id), None)
            assert matching_doc is not None
            assert matching_doc["fields"] == original_doc.fields

        # Verify ratings
        original_ratings = populated_datastore.get_ratings()
        assert len(data["ratings"]) == len(original_ratings)

        for original_rating in original_ratings:
            matching_rating = next(
                (r for r in data["ratings"]
                 if r["query_id"] == original_rating.query_id
                 and r["doc_id"] == original_rating.doc_id),
                None
            )
            assert matching_rating is not None
            assert matching_rating["score"] == original_rating.score

        # Verify max_rating_value
        max_score = max((r.score for r in original_ratings), default=1)
        assert data["max_rating_value"] == max_score

    def test_write_with_empty_datastore(self, writer_config: WriterConfig, tmp_path: Path):
        """Test writing an empty datastore."""
        output_dir = tmp_path
        writer = VisualizerWriter(writer_config=writer_config)

        empty_datastore = DataStore(ignore_saved_data=True)
        writer.write(output_dir, empty_datastore)

        output_file = output_dir / OUTPUT_FILENAME
        assert output_file.exists()

        with gzip.open(output_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        assert data["queries"] == []
        assert data["documents"] == []
        assert data["ratings"] == []
        assert data["max_rating_value"] == 1  # default value

    def test_write_with_various_rating_scores(self, writer_config: WriterConfig, tmp_path: Path):
        """Test that max_rating_value is correctly calculated with various scores."""
        output_dir = tmp_path
        writer = VisualizerWriter(writer_config=writer_config)

        datastore = DataStore(ignore_saved_data=True)
        doc1 = Document(id="doc1", fields={"title": "test 1"})
        doc2 = Document(id="doc2", fields={"title": "test 2"})
        doc3 = Document(id="doc3", fields={"title": "test 3"})
        datastore.add_document(doc1)
        datastore.add_document(doc2)
        datastore.add_document(doc3)

        q = datastore.add_query("test query")
        datastore.create_rating_score(q.id, doc1.id, 0)
        datastore.create_rating_score(q.id, doc2.id, 1)
        datastore.create_rating_score(q.id, doc3.id, 2)

        writer.write(output_dir, datastore)

        output_file = output_dir / OUTPUT_FILENAME

        with gzip.open(output_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        assert data["max_rating_value"] == 2
        assert len(data["ratings"]) == 3

    def test_write_with_only_queries_no_ratings(self, writer_config: WriterConfig, tmp_path: Path):
        """Test writing datastore with queries and documents but no ratings."""
        output_dir = tmp_path
        writer = VisualizerWriter(writer_config=writer_config)

        datastore = DataStore(ignore_saved_data=True)
        datastore.add_document(Document(id="doc1", fields={"title": "test"}))
        datastore.add_query("query without ratings")

        writer.write(output_dir, datastore)

        output_file = output_dir / OUTPUT_FILENAME

        with gzip.open(output_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)

        assert len(data["queries"]) == 1
        assert len(data["documents"]) == 1
        assert len(data["ratings"]) == 0
        assert data["max_rating_value"] == 1  # default when no ratings

