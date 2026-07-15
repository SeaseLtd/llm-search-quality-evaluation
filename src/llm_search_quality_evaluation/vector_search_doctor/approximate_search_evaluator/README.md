# Approximate Search Evaluator

This tool evaluates a search engine collection using IR metrics (nDCG, MAP, MRR, Precision, Recall)
computed in-process via [ranx](https://github.com/AmenRa/ranx). It is designed to test ANN
(approximate nearest neighbour) implementations and keyword search quality, including vector/hybrid
queries that require precomputed embeddings.

Input is an `evaluation_dataset.json.gz` file produced by the
[Dataset Generator](../../../dataset_generator/README.md) with `output_format: evaluation_dataset`.


## Setup configuration file

Create a config YAML file (or modify the
[example](../../../../examples/configs/vector_search_doctor/approximate_search_evaluator/approximate_search_evaluator_config.yaml)).

### Required fields

| Field | Description |
|---|---|
| `query_template` | Path to a query template file with `$query` (and optionally `$vector`) placeholders |
| `search_engine_type` | `"solr"`, `"elasticsearch"`, or `"opensearch"` (Vespa: deferred) |
| `collection_name` | Name of the search engine index/collection |
| `search_engine_url` | Base URL of the search engine (e.g. `"http://localhost:8983/solr/"`) |
| `evaluation_dataset_path` | Path to the `evaluation_dataset.json.gz` file |

### Optional fields

| Field | Default | Description |
|---|---|---|
| `id_field` | `"id"` (solr/opensearch), `"_id"` (elasticsearch) | Unique key field |
| `query_placeholder` | `"$query"` | Placeholder substituted with the query text in the template |
| `doc_fields` | `[]` | Document fields to request from the engine |
| `top_k` | `10` | Number of top results per query fed to the metrics |
| `metrics` | `["ndcg@10", "map@10", "mrr@10", "precision@10", "recall@10"]` | ranx metric names |
| `embeddings_folder` | `None` | Folder containing `queries_embeddings.jsonl` (required for vector queries) |
| `output_destination` | `"resources"` | Directory where `evaluation_results.json` is written |

> **Relevance threshold is derived, not configured.** It is computed as
> `(max_rating_value + 1) // 2` from the dataset's `max_rating_value` at runtime.
> Do not add it to the config.


## Output

`evaluation_results.json` written to `output_destination`:

```json
{
  "search_engine": { "type": "solr", "endpoint": "http://localhost:8983/solr/testcore/" },
  "query_template": "only_vector.json",
  "top_k": 10,
  "max_rating_value": 4,
  "relevance_threshold": 2,
  "num_queries": 30,
  "metrics": ["ndcg@10", "map@10"],
  "aggregate": { "ndcg@10": 0.73, "map@10": 0.61 },
  "per_query": {
    "some query text": {
      "num_retrieved": 10.0,
      "num_relevant_total": 5.0,
      "ndcg@10": 0.81,
      "map@10": 0.70
    }
  }
}
```


## Running

```bash
uv run approximate_search_evaluator --config <path-to-config-yaml>
```

Add `-v` / `--verbose` for debug logging.
