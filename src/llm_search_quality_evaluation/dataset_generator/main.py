from __future__ import annotations

# ------ temporary import for corpus.json bug workaround ------
import json
from pathlib import Path
from llm_search_quality_evaluation.shared.utils import _to_string
import argparse
# -------------------------------------------------------------

from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Callable, List, Tuple
from logging import Logger, getLogger

# project imports
from llm_search_quality_evaluation.shared.logger import setup_logging
from llm_search_quality_evaluation.dataset_generator.llm import (
    LLMConfig,
    LLMService,
    LLMServiceFactory,
    load_batch_prompt,
)
from llm_search_quality_evaluation.dataset_generator.llm.llm_provider_factory import LazyLLM
from llm_search_quality_evaluation.shared.models import Document, Query
from llm_search_quality_evaluation.shared.models.query import SOURCE_PRIORITY
from llm_search_quality_evaluation.shared.writers import WriterFactory, AbstractWriter, WriterConfig
from llm_search_quality_evaluation.shared.search_engines import SearchEngineFactory, BaseSearchEngine
from llm_search_quality_evaluation.shared.data_store import DataStore
from llm_search_quality_evaluation.shared.utils import join_fields_as_text

from llm_search_quality_evaluation.dataset_generator.models import LLMQueryResponse, LLMScoreResponse
from llm_search_quality_evaluation.dataset_generator.config import Config
from llm_search_quality_evaluation.dataset_generator.query_sources import add_category_queries

log: Logger = getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Parse arguments for CLI.')

    parser.add_argument('-c', '--config', type=str,
                        help='Config file path to use for the application [default: "examples/configs/dataset_generator/dataset_generator_config.yaml"]',
                        required=False, default="examples/configs/dataset_generator/dataset_generator_config.yaml")

    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Activate debug mode for logging [default: False]')

    return parser.parse_args()


def add_user_queries(config: Config, data_store: DataStore) -> None:
    """Loads queries from file (if exists) and adds them as Query objects."""
    if config.queries is not None:
        with config.queries.open("r", encoding="utf-8") as file:
            for line in file:
                clean_line = line.strip()
                if clean_line:
                    data_store.add_query(clean_line, source="user")
            log.info(f"Added user-defined queries from file={config.queries}")


def fetch_and_add_seed_documents(config: Config, data_store: DataStore,
                                 search_engine: BaseSearchEngine) -> List[Document]:
    """Fetch seed documents from the search engine and ensure each is flagged as a cartesian seed.

    Returns the list of fetched documents so callers can reuse them without re-fetching.
    """
    docs_to_generate_queries: List[Document] = search_engine.fetch_for_query_generation(
        documents_filter=config.documents_filter,
        number_of_docs=config.number_of_docs,
        doc_fields=config.doc_fields
    )

    for doc in docs_to_generate_queries:
        doc.is_used_to_generate_queries = True
        data_store.add_document(doc)
        # Cache hit path: add_document() returned early without updating the stored object.
        data_store.mark_document_as_query_seed(doc.id)

    return docs_to_generate_queries


def generate_and_add_queries_from_documents(config: Config, data_store: DataStore, llm_service: LLMService,
                                            seed_docs: List[Document]) -> None:
    """Generate and store LLM queries from fetched seed documents.

    Each query is pre-rated against its seed document with the maximum relevance label.
    Only sources with priority <= ``llm`` consume the generation budget.
    """
    llm_threshold = SOURCE_PRIORITY["llm"]

    def _slots_filled() -> int:
        return sum(1 for q in data_store.get_queries() if SOURCE_PRIORITY[q.source] <= llm_threshold)

    remaining = max(0, config.num_queries_needed - _slots_filled())
    if remaining == 0:
        return

    num_queries_per_doc: int = int((remaining // max(1, config.number_of_docs)) + 1)  # always greater or equal to 1
    log.debug(f"Number of documents retrieved for generation: {len(seed_docs)}")
    log.debug(f"Pending queries to generate: {remaining}")
    log.debug(f"Number of queries per document: {num_queries_per_doc}")

    def _apply_response(doc: Document, query_response: LLMQueryResponse) -> bool:
        """Apply a single doc's LLM response. Returns False once the budget is full."""
        for query_ in query_response.get_queries():
            if _slots_filled() >= config.num_queries_needed:
                return False
            query_obj: Query = data_store.add_query(query_, source="llm")
            data_store.create_rating_score(
                query_obj.id, doc.id, max(config.relevance_label_set),
                "Default max rating is assigned because the query is generated by the document"
            )
        return True

    if config.llm_max_workers == 1:
        for doc in seed_docs:
            # Re-check between outer iterations so we don't burn an LLM call on doc N+1
            # after the inner loop on doc N already filled the budget.
            if _slots_filled() >= config.num_queries_needed:
                return
            query_response: LLMQueryResponse = llm_service.generate_queries(
                doc, num_queries_per_doc, config.max_query_terms
            )
            if not _apply_response(doc, query_response):
                return
        return

    # Apply parallel results in seed-document order, not completion order, to keep
    # the stored queries, budget cutoff, and deduplication deterministic.
    def _gen_queries_for_doc(doc: Document) -> Tuple[Document, LLMQueryResponse]:
        return doc, llm_service.generate_queries(doc, num_queries_per_doc, config.max_query_terms)

    def _log_unobserved_failure(fut: "Future[Tuple[Document, LLMQueryResponse]]") -> None:
        # concurrent.futures.Future does not log unretrieved exceptions, so report them here.
        if fut.cancelled():
            return
        error = fut.exception()
        if error is not None:
            log.warning("Query generation worker failed: %s", error)

    with ThreadPoolExecutor(max_workers=config.llm_max_workers) as executor:
        doc_futures: List[Tuple[Document, "Future[Tuple[Document, LLMQueryResponse]]"]] = []
        for doc in seed_docs:
            fut = executor.submit(_gen_queries_for_doc, doc)
            fut.add_done_callback(_log_unobserved_failure)
            doc_futures.append((doc, fut))
        for doc, fut in doc_futures:
            # Unawaited futures still run on shutdown; callbacks log their failures.
            if _slots_filled() >= config.num_queries_needed:
                return
            _, query_response = fut.result()  # awaited: LLM exceptions propagate
            if not _apply_response(doc, query_response):
                return


def get_queries_within_budget(config: Config, data_store: DataStore) -> List[Query]:
    """Pick the per-run query budget, prioritizing fresh sources over cached ones.

    Stable sort by `(SOURCE_PRIORITY[query.source], insertion_index)` so user/category
    queries asserted this run always make the cut before queries loaded from the disk
    cache, while preserving insertion order within each priority tier.
    """
    queries = data_store.get_queries()
    indexed = list(enumerate(queries))
    indexed.sort(key=lambda iq: (SOURCE_PRIORITY[iq[1].source], iq[0]))
    queries_within_budget = [q for _, q in indexed[:config.num_queries_needed]]
    if len(queries) > len(queries_within_budget):
        log.info(
            "Processing %s of %s queries due to num_queries_needed=%s",
            len(queries_within_budget),
            len(queries),
            config.num_queries_needed,
        )
    return queries_within_budget


def score_docs_for_query(
    config: Config,
    data_store: DataStore,
    llm_service: LLMService,
    prompt_template: str,
    query: Query,
    documents: List[Document],
) -> None:
    """Score unrated documents with single or batched calls per LLM micro-batch size.

    Already-rated pairs are skipped. Duplicate documents are dropped (first wins)
    because the batch contract requires one item per input document.
    """
    pending: List[Document] = []
    seen_ids: set[str] = set()
    for d in documents:
        if d.id in seen_ids:
            continue
        if data_store.has_rating_score(query.id, d.id):
            continue
        seen_ids.add(d.id)
        pending.append(d)
    if not pending:
        return

    if config.llm_micro_batch_size == 1:
        for doc in pending:
            resp: LLMScoreResponse = llm_service.generate_score(
                doc, query.text, config.relevance_scale, config.save_llm_explanation
            )
            data_store.create_rating_score(
                query.id, doc.id, resp.get_score(),
                resp.explanation if config.save_llm_explanation else None,
            )
        return

    for i in range(0, len(pending), config.llm_micro_batch_size):
        batch = pending[i : i + config.llm_micro_batch_size]
        ratings = llm_service.generate_scores_batch(
            query_id=query.id,
            query_text=query.text,
            documents=batch,
            relevance_scale=config.relevance_scale,
            explanation=config.save_llm_explanation,
            prompt_template=prompt_template,
            max_retries=config.llm_batch_max_retries,
        )
        for doc in batch:
            resp = ratings[doc.id]
            data_store.create_rating_score(
                query.id, doc.id, resp.get_score(),
                resp.explanation if config.save_llm_explanation else None,
            )


def _run_per_query(config: Config, queries: List[Query], work_fn: Callable[[Query], None]) -> None:
    """Run work sequentially with one worker or in a thread pool otherwise.
    Worker exceptions propagate to the caller.
    """
    if config.llm_max_workers == 1:
        for q in queries:
            work_fn(q)
        return

    with ThreadPoolExecutor(max_workers=config.llm_max_workers) as executor:
        futures = [executor.submit(work_fn, q) for q in queries]
        for fut in as_completed(futures):
            fut.result()  # propagates any worker exception


def add_cartesian_product_scores(config: Config, data_store: DataStore, llm_service: LLMService,
                                 prompt_template: str) -> None:
    """Complete the (query, doc) matrix with LLM scores."""
    log.debug("Cartesian product is enabled, so adding cartesian product scores")

    def _work(query_obj: Query) -> None:
        docs = data_store.get_cartesian_prod_docs()
        score_docs_for_query(config, data_store, llm_service, prompt_template, query_obj, docs)

    _run_per_query(config, get_queries_within_budget(config, data_store), _work)


def expand_docset_with_search_engine_top_k(config: Config, data_store: DataStore,
                                           llm_service: LLMService, search_engine: BaseSearchEngine,
                                           prompt_template: str) -> None:
    """Retrieve docs for each query and score the (q, doc) pairs."""
    if config.query_template is None:
        log.warning("Query template not found. Skipping retrieval.")
        return

    # Bind the narrowed (non-None) template into a local so the closure below captures a
    # concrete Path rather than the Optional config attribute.
    query_template = config.query_template
    log.debug(f"Searching for documents with query template in {query_template}")

    def _work(query_obj: Query) -> None:
        docs_eval: List[Document] = search_engine.fetch_for_evaluation(
            keyword=query_obj.text, query_template=query_template, doc_fields=config.doc_fields
        )
        for doc_obj in docs_eval:
            data_store.add_document(doc_obj)
        score_docs_for_query(config, data_store, llm_service, prompt_template, query_obj, docs_eval)

    _run_per_query(config, get_queries_within_budget(config, data_store), _work)


def main() -> None:
    # configuration and logger definition
    args = parse_args()
    config: Config = Config.load(args.config)
    writer_config: WriterConfig = config.build_writer_config()
    setup_logging(args.verbose)

    # setup
    data_store: DataStore = DataStore(
        autosave_every_n_updates=config.datastore_autosave_every_n_updates
    )
    search_engine: BaseSearchEngine = SearchEngineFactory.build(
        search_engine_type=config.search_engine_type,
        endpoint=config.search_engine_collection_endpoint
    )
    llm: LazyLLM = LLMServiceFactory.build_lazy(LLMConfig.load(config.llm_configuration_file))
    service: LLMService = LLMService(chat_model=llm)
    writer: AbstractWriter = WriterFactory.build(writer_config)

    # Wrap every datastore-mutating step so any failure (LLM error,
    # search-engine timeout, plain bug) still leaves whatever was added in
    # memory durable on disk. The scoping covers query generation (which
    # adds queries and pre-ratings) and seed-fetch too, not just scoring —
    # an LLM failure mid-query-gen used to lose the responses that had
    # already been applied. The inner try/except around save() means a
    # save failure logs but doesn't mask the original exception (operators
    # care about the root failure, not the save aftermath).
    try:
        # load user queries
        add_user_queries(config, data_store)

        # render category-derived queries from each source's explicit values, or from values
        # discovered by the engine when values_query_template_file is set instead of values.
        add_category_queries(config, data_store, search_engine)

        # fetch seed documents only when something downstream actually needs them
        seed_docs: List[Document] = []
        if config.enable_cartesian_product or config.generate_queries_from_documents:
            seed_docs = fetch_and_add_seed_documents(config, data_store, search_engine)

        # generate more queries with LLM service from the same seed documents, if enabled
        if config.generate_queries_from_documents:
            generate_and_add_queries_from_documents(config, data_store, service, seed_docs)

        # Resolve the batch-scoring prompt template once. Reads `llm_batch_score_prompt`
        # from disk if set, otherwise returns the built-in default. Always called so
        # `score_docs_for_query` can pass a concrete string into the LLM service —
        # the dispatch on `llm_micro_batch_size == 1` ignores the template, but it
        # costs nothing to resolve it eagerly and keeps the helper signature uniform.
        batch_prompt_template: str = load_batch_prompt(config.llm_batch_score_prompt)

        # score initial docset
        if config.enable_cartesian_product:
            add_cartesian_product_scores(config, data_store, service, batch_prompt_template)

        # expand the docset with search engine topK (adding direct ratings)
        expand_docset_with_search_engine_top_k(config, data_store, service, search_engine,
                                               batch_prompt_template)
    except Exception:
        try:
            data_store.save()
        except Exception:
            log.exception("Failed to save datastore while handling work-phase failure")
        raise

    # write results
    output_destination = config.output_destination
    log.info(f"Synthetic Dataset has been generated in: {output_destination}")
    data_store.save()
    writer.write(output_destination, data_store)

    # save explanation  - forced to extract value before invoking export_all_records_with_explanation (mypy)
    if config.save_llm_explanation:
        if llm_explanation_path := config.llm_explanation_destination:
            data_store.export_all_records_with_explanation(llm_explanation_path)
            log.info(f"Dataset with LLM explanation is saved into: {llm_explanation_path}")

    # Replace the MTEB corpus so it includes all documents fetched from the search engine.
    if config.output_format == "mteb":
        corpus_path = Path(output_destination) / "corpus.jsonl"
        corpus_path.unlink(missing_ok=True)
        with corpus_path.open("a", encoding="utf-8") as file:
            for doc in search_engine.fetch_all(doc_fields=config.doc_fields):
                doc_id = str(doc.id)
                fields = doc.fields
                title = _to_string(fields.get("title"))
                text = join_fields_as_text(fields=fields, exclude={'id', 'title'})

                row = {"id": doc_id, "title": title, "text": text}
                file.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
