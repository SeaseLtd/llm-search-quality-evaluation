"""Unit tests for the Solr facet value-discovery parser.

Covers the happy path plus malformed-response shapes that previously escaped the
node checks and surfaced as an opaque ``TypeError`` from an indexing attempt.
"""
from __future__ import annotations

import pytest

from llm_search_quality_evaluation.shared.search_engines.solr_search_engine import SolrSearchEngine


def test_alternating_array_drops_counts_and_preserves_order():
    body = {"facet_counts": {"facet_fields": {"genres": ["comedy", 12, "action", 4]}}}
    assert SolrSearchEngine._list_values_from_facet_fields(body, "genres") == ["comedy", "action"]


@pytest.mark.parametrize(
    "body, expected_message",
    [
        (["facet_counts"], "expected a JSON object response"),
        ({"facet_counts": ["facet_fields"]}, "expected facet_counts to be an object"),
        ({"facet_counts": "facet_fields"}, "expected facet_counts to be an object"),
        ({}, "expected facet_counts to be an object"),
        ({"facet_counts": {}}, "expected facet_counts.facet_fields to be an object"),
        (
            {"facet_counts": {"facet_fields": ["genres"]}},
            "expected facet_counts.facet_fields to be an object",
        ),
        (
            {"facet_counts": {"facet_fields": {"category": ["x", 1]}}},
            "expected facet_counts.facet_fields.genres in response",
        ),
        (
            {"facet_counts": {"facet_fields": {"genres": "comedy,action"}}},
            "must be a list",
        ),
        (
            {"facet_counts": {"facet_fields": {"genres": ["comedy", 1, "action"]}}},
            "must have even length",
        ),
    ],
)
def test_malformed_responses_raise_value_error(body, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        SolrSearchEngine._list_values_from_facet_fields(body, "genres")
