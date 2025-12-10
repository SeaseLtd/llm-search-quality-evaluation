"""
llm_provider_factory.py

Provides a simple Factory for creating LangChain ChatModel instances
with lazy initialization for the 2 currently supported LLMs - openai and gemini.

"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from llm_search_quality_evaluation.dataset_generator.llm.llm_config import LLMConfig

log = logging.getLogger(__name__)


def build_openai(config: LLMConfig) -> BaseChatModel:
    load_dotenv()  # load .env file
    key = os.getenv(config.api_key_env or "OPENAI_API_KEY")
    if not key:
        log.error("OpenAI API key not set %s in the env", config.api_key_env)
        raise ValueError("OpenAI API key not set.")
    log.debug("Building OpenAI ChatModel using name=%s, model=%s, reasoning_effort=%s",
              config.name, config.model, config.reasoning_effort)
    if config.reasoning_effort is None:
        return ChatOpenAI(
            model=config.model,
            api_key=SecretStr(key),
        )
    else:
        return ChatOpenAI(
            model=config.model,
            api_key=SecretStr(key),
            reasoning_effort=config.reasoning_effort,
        )


def build_gemini(config: LLMConfig) -> BaseChatModel:
    load_dotenv()  # load .env file
    key = os.getenv(config.api_key_env or "GOOGLE_API_KEY")
    if not key:
        log.error("Google Gemini API key not set %s in the env", config.api_key_env)
        raise ValueError("Google Gemini API key not set.")
    log.debug("Building Google Gemini ChatModel using name=%s, model=%s, reasoning_effort=%s",
              config.name, config.model, config.reasoning_effort)
    return ChatGoogleGenerativeAI(
        model=config.model,
        google_api_key=key,
        model_kwargs={
            "thinking_config": {
                "thinking_budget": config.reasoning_effort,
            }
        }
    )


class LazyLLM:
    def __init__(self, config: LLMConfig):
        self.config = config
        self._llm: Optional[BaseChatModel] = None

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            log.info("Initializing LLM for the first time: provider=%s, model=%s",
                    self.config.name, self.config.model)
            self._llm = LLMServiceFactory.build(self.config)
        return self._llm

    def __getattr__(self, name):  # type: ignore[no-untyped-def]
        return getattr(self.llm, name)


class LLMServiceFactory:
    PROVIDER_REGISTRY = {
        "openai": build_openai,
        "gemini": build_gemini,
    }
    _cache: Optional[LazyLLM] = None

    @classmethod
    def build(cls, config: LLMConfig) -> BaseChatModel:
        provider_name = config.name
        provider_model = config.model
        if provider_name not in cls.PROVIDER_REGISTRY:
            log.error("Unsupported LLM provider requested: %s", provider_name)
            raise ValueError(f"Unsupported provider: {provider_name}")
        log.info("Building LLM provider=%s, model=%s", provider_name, provider_model)
        return cls.PROVIDER_REGISTRY[provider_name](config)

    @classmethod
    def build_lazy(cls, config: LLMConfig) -> LazyLLM:
        if cls._cache is None:
            log.debug("Creating lazy LLM wrapper for: provider=%s, model=%s", config.name, config.model)
            cls._cache = LazyLLM(config)
        else:
            log.debug("Reusing cached lazy LLM wrapper for: provider=%s, model=%s", config.name, config.model)

        return cls._cache
