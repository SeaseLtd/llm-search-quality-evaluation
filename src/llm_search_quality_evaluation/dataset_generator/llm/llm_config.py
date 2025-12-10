from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

log = logging.getLogger(__name__)


class LLMConfig(BaseModel):
    name: Literal['openai', 'gemini']
    model: str
    reasoning_effort: Optional[str] = Field(default=None, description="The reasoning effort of the model")
    api_key_env: Optional[str] = None

    @model_validator(mode="after")
    def set_reasoning_effort_defaults(self) -> "LLMConfig":
        if self.name == "openai":
            default_effort_mode = "minimal"
            effort_list = ["minimal", "low", "medium", "high"]
        else:
            default_effort_mode = "low"
            effort_list = ["low", "high"]

        if self.reasoning_effort not in effort_list and self.reasoning_effort is not None:
            self.reasoning_effort = default_effort_mode

        return self


    @classmethod
    def load(cls, path: str | Path = "llm_config.yaml") -> LLMConfig:
        path = Path(path).resolve()
        if not path.exists():
            log.error("LLM config file not found: %s", path)
            raise FileNotFoundError(f"LLM config file not found: {path}")
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
            log.debug("LLM configuration file loaded successfully")
        return cls(**raw)
