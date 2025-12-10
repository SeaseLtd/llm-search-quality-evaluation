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
