import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic_core import ValidationError

from llm_search_quality_evaluation.dataset_generator.llm import LLMConfig, LLMService
from llm_search_quality_evaluation.dataset_generator.llm.llm_provider_factory import LazyLLM, LLMServiceFactory
from llm_search_quality_evaluation.shared.models import Document


@pytest.fixture
def example_doc():
    """Provides a sample Document object for testing."""
    return Document(
        id="doc1",
        fields={
            "title": "Car of the Year",
            "description": "The Toyota Camry, the nation's most popular car has now been rated as its best new model."
        }
    )


@pytest.fixture
def query():
    return "Is a Toyota the car of the year?"


def test_llm_factory_lazy__expected__llm_none():
    cfg = LLMConfig(
        name="openai",
        model="mock_model",
        max_tokens= 1024,
        api_key_env="mock_api_key",
    )
    llm: LazyLLM = LLMServiceFactory.build_lazy(cfg)
    assert llm._llm is None

def test_llm_factory_invalid_model_name__expected__validation_error():
    with pytest.raises(ValidationError):
        _ = LLMConfig(
            name="mock_provider",
            model="mock_model",
            max_tokens= 1024,
            api_key_env="mock_api_key",
        )



@pytest.mark.parametrize("provider, model", [
    ("openai", "gpt-5-nano-2025-08-07"),
    ("gemini", "gemini-3-pro-preview"),
])
def test_llm_factory_lazy_openai__expected__api_key_not_valid(example_doc, query, provider, model):
    cfg = LLMConfig(
        name=provider,
        model=model,
        max_tokens=1024,
        api_key_env="invalid_api_key",
    )
    llm: LazyLLM = LLMServiceFactory.build_lazy(cfg)

    service: LLMService = LLMService(chat_model=llm)
    with pytest.raises(ValueError):
        _ = service.generate_score(example_doc, query, relevance_scale='binary')


def test_lazy_llm_builds_model_once_under_concurrency(monkeypatch):
    """Concurrent first-use of LazyLLM.llm must build the underlying model exactly once.

    The PR runs scoring / query-gen through a ThreadPoolExecutor when llm_max_workers > 1.
    Without the double-checked lock in LazyLLM.llm, racing workers could each see
    `_llm is None` and call LLMServiceFactory.build redundantly. This asserts a single build.
    """
    cfg = LLMConfig(
        name="openai",
        model="mock_model",
        max_tokens=1024,
        api_key_env="mock_api_key",
    )

    build_calls = 0
    build_calls_lock = threading.Lock()

    class _DummyModel:
        def with_structured_output(self, *_args, **_kwargs):
            return self

    def fake_build(config):
        nonlocal build_calls
        with build_calls_lock:
            build_calls += 1
        # Widen the race window so a missing lock would be caught reliably.
        time.sleep(0.01)
        return _DummyModel()

    monkeypatch.setattr(LLMServiceFactory, "build", staticmethod(fake_build))
    # Isolate from the class-level cache: construct LazyLLM directly so this test's result
    # cannot be influenced by (or leak into) LLMServiceFactory._cached_lazy_llm.
    monkeypatch.setattr(LLMServiceFactory, "_cached_lazy_llm", None, raising=False)

    lazy = LazyLLM(cfg)

    n_workers = 16
    barrier = threading.Barrier(n_workers)

    def worker():
        barrier.wait()  # release all threads together to maximize the race
        return lazy.with_structured_output(object)

    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        results = [f.result() for f in [executor.submit(worker) for _ in range(n_workers)]]

    assert build_calls == 1
    assert all(r is not None for r in results)
