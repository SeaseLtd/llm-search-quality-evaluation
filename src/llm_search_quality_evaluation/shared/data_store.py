from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import json
import logging
from uuid import uuid4
from pydantic import ValidationError
from llm_search_quality_evaluation.shared.models.document import Document
from llm_search_quality_evaluation.shared.models.query import Query, QuerySource, SOURCE_PRIORITY
from llm_search_quality_evaluation.shared.models.rating import Rating
from llm_search_quality_evaluation.shared.utils import clean_text

log = logging.getLogger(__name__)

TMP_FILE = Path("resources/tmp/datastore.json")
ENCODING = "utf-8"


class DataStore:
    """Hold documents, queries, and ratings with O(1) indices.

    Each ``(query_id, doc_id)`` pair has at most one rating.
    ``has_rating_score`` is true only when that ``Rating`` exists.
    A single ``RLock`` makes public operations thread-safe at container level.
    Getter snapshots are container-safe but contain the live mutable objects.
    Callers must sequence operations that require consistent object fields.
    Separate existence checks and creates are not atomic; creates are idempotent.
    Autosave captures partial progress and may persist snapshots out of order.
    The final ``save()`` is authoritative.
    """

    def __init__(self, path: Path = TMP_FILE, ignore_saved_data: bool = False, autosave_every_n_updates: Optional[int] = None):
        # ORDER MATTERS: assign self._lock BEFORE calling self.load(). load()
        # invokes add_document / add_query / _add_rating, each of which
        # acquires self._lock — moving this line below self.load() makes the
        # first record loaded raise `AttributeError: 'DataStore' object has
        # no attribute '_lock'`. Guarded by
        # test_data_store__load_called_inside_init__lock_already_initialized.
        self._lock = threading.RLock()
        self.path = path
        # Autosave configuration: when >0, save to disk every N successful mutations
        self._autosave_every_n_updates: Optional[int] = (
            autosave_every_n_updates if isinstance(autosave_every_n_updates, int) and autosave_every_n_updates > 0 else None
        )
        self._updates_since_last_save: int = 0

        # Primary (id → object)
        self.docs: Dict[str, Document] = {}
        self.queries: Dict[str, Query] = {}

        # Ratings storage
        self.rating_by_pair: Dict[Tuple[str, str], Rating] = {}    # (query_id, doc_id) → Rating

        # Text based deduplication for queries
        self.query_text_to_query_id: Dict[str, str] = {}           # query_text → query_id

        if not ignore_saved_data:
            log.info(f"Loading data from {path}")
            self.load()

    # ────────────────────────────────────────────
    # Existence checks
    # ────────────────────────────────────────────
    def has_document(self, doc_id: str) -> bool:
        with self._lock:
            return doc_id in self.docs

    def has_query(self, query_id: str) -> bool:
        with self._lock:
            return query_id in self.queries

    def has_rating_score(self, query_id: str, doc_id: str) -> bool:
        with self._lock:
            return (query_id, doc_id) in self.rating_by_pair

    # ────────────────────────────────────────────
    # Getters
    # ────────────────────────────────────────────
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Gets a single document by its ID, or None if not found."""
        with self._lock:
            return self.docs.get(doc_id)

    def get_documents(self) -> List[Document]:
        with self._lock:
            return list(self.docs.values())

    def get_cartesian_prod_docs(self) -> List[Document]:
        """Gets only documents used to generate queries."""
        with self._lock:
            return [doc for doc in self.docs.values() if doc.is_used_to_generate_queries]

    def get_query(self, query_id: str) -> Optional[Query]:
        """Gets a single query by its ID, or None if not found."""
        with self._lock:
            return self.queries.get(query_id)

    def get_queries(self) -> List[Query]:
        with self._lock:
            return list(self.queries.values())

    def get_ratings(self) -> List[Rating]:
        with self._lock:
            return list(self.rating_by_pair.values())


    # ────────────────────────────────────────────
    # Mutators (all O(1) on average)
    # ────────────────────────────────────────────
    def add_document(self, doc: Document) -> None:
        snapshot: Optional[Dict[str, Any]] = None
        with self._lock:
            if doc.id in self.docs:
                log.debug(f"[add_document] exists doc_id={doc.id}")
                return
            self.docs[doc.id] = doc
            log.debug(f"[add_document] added doc_id={doc.id}")
            snapshot = self._capture_autosave_snapshot_if_due()
        self._persist_autosave(snapshot)

    def mark_document_as_query_seed(self, doc_id: str) -> None:
        """Flag an already-stored document as a cartesian seed.

        Required because add_document() returns early when doc_id already
        exists, so a re-fetched doc cannot update the stored object's
        is_used_to_generate_queries flag through that path.
        """
        snapshot: Optional[Dict[str, Any]] = None
        with self._lock:
            doc = self.docs.get(doc_id)
            if doc is None:
                log.warning(f"[mark_document_as_query_seed] doc_not_found doc_id={doc_id}")
                return
            if not doc.is_used_to_generate_queries:
                doc.is_used_to_generate_queries = True
                snapshot = self._capture_autosave_snapshot_if_due()
        self._persist_autosave(snapshot)

    def add_query(self, query_text_str: str, query_id: Optional[str] = None,
                  source: Optional[QuerySource] = None) -> Query:
        """Add a query or return one deduplicated by cleaned text.

        Use a provided ID and promote an existing query to a higher-priority source.
        """
        key = clean_text(query_text_str) # Apply general filtering
        snapshot: Optional[Dict[str, Any]] = None
        with self._lock:
            if existing_id := self.query_text_to_query_id.get(key):
                log.debug(f"[add_query] exists text='{query_text_str}' key='{key}' existing_id={existing_id}")
                query = self.queries[existing_id]
                if source is not None and SOURCE_PRIORITY[source] < SOURCE_PRIORITY[query.source]:
                    log.debug(f"[add_query] promote source {query.source}->{source} for query_id={query.id}")
                    query.source = source
            else:
                kwargs: Dict[str, Any] = {"text": query_text_str}
                if query_id:
                    kwargs["id"] = query_id
                if source is not None:
                    kwargs["source"] = source
                query = Query(**kwargs)
                self.queries[query.id] = query
                self.query_text_to_query_id[key] = query.id
                log.debug(f"[add_query] added query_id={query.id} source={query.source}")
                snapshot = self._capture_autosave_snapshot_if_due()

        self._persist_autosave(snapshot)
        return query

    def _add_rating(self, rating: Rating) -> Optional[Dict[str, Any]]:
        """Add a rating; return an autosave snapshot if one is due.

        Caller must hold ``self._lock`` and persist the result after releasing it.
        """
        if rating.query_id not in self.queries:
            log.warning(f"[add_rating] query_not_found query_id={rating.query_id}")
            return None
        if rating.doc_id not in self.docs:
            log.warning(f"[add_rating] doc_not_found doc_id={rating.doc_id}")
            return None

        key = (rating.query_id, rating.doc_id)
        if key in self.rating_by_pair:
            log.warning(f"[add_rating] exists q={rating.query_id} d={rating.doc_id}")
            return None

        self.rating_by_pair[key] = rating
        log.debug(f"[add_rating] added q={rating.query_id} d={rating.doc_id}")
        return self._capture_autosave_snapshot_if_due()

    def create_rating_score(
        self, query_id: str, doc_id: str, score: int, explanation: Optional[str] = None
    ) -> Optional[Rating]:
        """Create a rating or return the existing rating for the pair.

        Lookup and insertion are atomic; autosave persistence follows lock release.
        """
        snapshot: Optional[Dict[str, Any]] = None
        rating: Optional[Rating] = None
        with self._lock:
            key = (query_id, doc_id)
            if (existing_rating := self.rating_by_pair.get(key)):
                log.warning(f"[create_rating_score] existing q={query_id} d={doc_id}")
                return existing_rating

            try:
                rating = Rating(doc_id=doc_id, query_id=query_id, score=score, explanation=explanation)
                snapshot = self._add_rating(rating)
            except ValidationError as e:
                log.warning(f"[create_rating_score] validation_failed q={query_id} d={doc_id} score={score} error={e}")
                return None

        self._persist_autosave(snapshot)
        return rating

    # ────────────────────────────────────────────
    # Autosave helpers
    # ────────────────────────────────────────────
    def _capture_autosave_snapshot_if_due(self) -> Optional[Dict[str, Any]]:
        """Return a JSON-ready snapshot when autosave is due, otherwise None.

        Caller must hold ``self._lock``. The counter resets when the snapshot
        is captured, before persistence is attempted.
        """
        if self._autosave_every_n_updates is None:
            return None
        self._updates_since_last_save += 1
        if self._updates_since_last_save < self._autosave_every_n_updates:
            return None
        self._updates_since_last_save = 0
        return self._build_snapshot_unlocked()

    def _build_snapshot_unlocked(self) -> Dict[str, Any]:
        """Materialize a JSON-ready snapshot of the store. Caller must hold ``self._lock``."""
        return {
            "docs": [d.model_dump() for d in self.docs.values()],
            "queries": [q.model_dump() for q in self.queries.values()],
            "ratings": [r.model_dump() for r in self.rating_by_pair.values()],
        }

    def _write_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Atomically write a snapshot through a unique temporary path."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + f".{uuid4().hex}.tmp")
        tmp_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding=ENCODING)
        tmp_path.replace(self.path)

    def _persist_autosave(self, snapshot: Optional[Dict[str, Any]]) -> None:
        """Best-effort write a captured autosave snapshot. No-op if None.

        Log write errors instead of raising them to the mutator.
        """
        if snapshot is None:
            return
        # Calling save() while holding the lock serializes workers on file I/O.
        try:
            self._write_snapshot(snapshot)
            log.debug(f"[autosave] ok path={self.path}")
        except Exception as e:
            log.error(
                f"[autosave] failed to save {self.path}. Error: {e}",
                exc_info=True,
            )

    # ────────────────────────────────────────────
    # Persistence
    # ────────────────────────────────────────────
    def save(self) -> None:
        """Persist a locked snapshot, performing file I/O after lock release."""
        with self._lock:
            snapshot = self._build_snapshot_unlocked()
        self._write_snapshot(snapshot)

    def load(self) -> None:
        """Replay a persisted store from disk.

        Suppress autosave during replay, then reset the mutation counter.
        """
        with self._lock:
            if not self.path.exists():
                return

            # Clear previous data
            self._clear_all_data()

            try:
                data = json.loads(self.path.read_text(encoding=ENCODING))
            except json.JSONDecodeError as e:
                log.warning(f"Could not read datastore {self.path} (JSON). Starting clean. Error: {e}")
                return

            saved_threshold = self._autosave_every_n_updates
            self._autosave_every_n_updates = None
            try:
                # docs
                for doc_as_dict in data.get("docs", []):
                    try:
                        self.add_document(Document.model_validate(doc_as_dict))
                    except ValidationError as e:
                        log.warning(f"[load] skip_doc_invalid data={doc_as_dict} error={e}")

                # queries
                for query_as_dict in data.get("queries", []):
                    try:
                        tmp_query = Query.model_validate(query_as_dict)                # Create a new tmp query with loaded dict
                        self.add_query(query_text_str=tmp_query.text, query_id=tmp_query.id) # Pass (text, ID) values to keep ID consistent
                    except ValidationError as e:
                        log.warning(f"[load] skip_query_invalid data={query_as_dict} error={e}")

                # ratings
                for rating_as_dict in data.get("ratings", []):
                    try:
                        robj = Rating.model_validate(rating_as_dict)
                        self._add_rating(robj)
                    except ValidationError as e:
                        log.warning(f"[load] skip_rating_invalid data={rating_as_dict} error={e}")
            finally:
                self._autosave_every_n_updates = saved_threshold
                self._updates_since_last_save = 0

    def _clear_all_data(self) -> None:
        """Reset state. Caller must hold ``self._lock``."""
        self.docs.clear()
        self.queries.clear()
        self.rating_by_pair.clear()
        self.query_text_to_query_id.clear()


    def export_all_records_with_explanation(self, output_path: str | Path) -> None:
        """Export (query_text, doc_id, rating, explanation) to JSON."""
        with self._lock:
            records = []
            for rating_obj in self.rating_by_pair.values():
                # Guard against dangling references (defensive)
                query_obj = self.queries.get(rating_obj.query_id)
                if not query_obj:
                    continue
                records.append({
                    "query": query_obj.text,
                    "doc_id": rating_obj.doc_id,
                    "rating": rating_obj.score,
                    "explanation": rating_obj.explanation or ""
                })

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_path.open("w", encoding=ENCODING) as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            log.info(f"[export] ok path={output_path} records={len(records)}")
        except Exception as e:
            log.warning(f"[export] fail path={output_path} err={e}")
