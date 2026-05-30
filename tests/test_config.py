from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from unittest.mock import patch

from pi_sync.config import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_ID,
    DEFAULT_PROVIDER_ID,
    default_config,
    find_config_path,
    find_provider_by_url,
    generate_display_name,
    load_config,
    parse_jsonc,
    save_config,
    update_provider_models,
)
from tests.conftest import SAMPLE_CONFIG, SAMPLE_JSONC


def model_ids(config: dict, provider: str = DEFAULT_PROVIDER_ID) -> list[str]:
    return [m["id"] for m in config["providers"][provider]["models"]]


def model_by_id(config: dict, model_id: str, provider: str = DEFAULT_PROVIDER_ID) -> dict:
    return next(m for m in config["providers"][provider]["models"] if m["id"] == model_id)


def test_parse_jsonc_comments_and_trailing_commas():
    assert parse_jsonc(SAMPLE_JSONC)["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == "http://localhost:8080/v1"


def test_default_config_matches_local_llama_template():
    config = default_config()
    provider = config["providers"][DEFAULT_PROVIDER_ID]
    assert provider["baseUrl"] == DEFAULT_BASE_URL
    assert provider["api"] == "openai-completions"
    assert provider["apiKey"] == "llama"
    assert provider["compat"]["supportsDeveloperRole"] is False
    assert provider["models"][0]["id"] == DEFAULT_MODEL_ID


def test_find_config_path_uses_pi_agent_dir(tmp_path):
    with patch.dict(os.environ, {"PI_CODING_AGENT_DIR": str(tmp_path)}):
        assert find_config_path() == tmp_path / "models.json"


def test_find_config_path_defaults_to_home_pi_agent(tmp_path, monkeypatch):
    monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    assert find_config_path() == tmp_path / ".pi" / "agent" / "models.json"


def test_load_save_round_trip(tmp_path):
    cfg = tmp_path / "models.json"
    save_config(cfg, SAMPLE_CONFIG)
    assert load_config(cfg) == SAMPLE_CONFIG
    assert json.loads(cfg.read_text()) == SAMPLE_CONFIG


def test_generate_display_name_strips_org_prefix():
    assert generate_display_name("Qwen/Qwen3-27B") == "Qwen3-27B"


def test_find_provider_by_url_uses_base_url():
    config = {"providers": {"local": {"baseUrl": "http://localhost:8080/v1/"}}}
    assert find_provider_by_url(config, "http://localhost:8080/v1") == "local"
    assert find_provider_by_url(config, "http://other:8080/v1") is None


def test_update_provider_models_adds_and_removes_models():
    updated, added, removed = update_provider_models(
        SAMPLE_CONFIG, DEFAULT_PROVIDER_ID, ["org/model-a", "org/model-c"]
    )
    assert added == ["org/model-c"]
    assert removed == ["org/model-b"]
    assert model_ids(updated) == ["org/model-a", "org/model-c"]


def test_update_provider_models_preserves_existing_model_metadata():
    updated, _, _ = update_provider_models(SAMPLE_CONFIG, DEFAULT_PROVIDER_ID, ["org/model-a"])
    assert model_by_id(updated, "org/model-a")["name"] == "Model A"


def test_update_provider_models_adds_pi_model_defaults():
    updated, _, _ = update_provider_models(SAMPLE_CONFIG, DEFAULT_PROVIDER_ID, ["org/new-model"])
    model = model_by_id(updated, "org/new-model")
    assert model["name"] == "new-model"
    assert model["input"] == ["text"]
    assert model["contextWindow"] == 32768
    assert model["maxTokens"] == 8192


def test_update_provider_models_updates_base_url_when_provided():
    updated, _, _ = update_provider_models(
        SAMPLE_CONFIG, DEFAULT_PROVIDER_ID, ["org/model-a"], base_url="http://remote:9000/v1"
    )
    assert updated["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == "http://remote:9000/v1"


def test_update_provider_models_creates_provider_from_empty_config():
    updated, _, _ = update_provider_models({}, "my-local", ["some/model"])
    provider = updated["providers"]["my-local"]
    assert provider["api"] == "openai-completions"
    assert provider["apiKey"] == "llama"
    assert model_ids(updated, "my-local") == ["some/model"]


def test_update_provider_models_does_not_mutate_original():
    config = copy.deepcopy(SAMPLE_CONFIG)
    original = copy.deepcopy(config)
    update_provider_models(config, DEFAULT_PROVIDER_ID, ["org/model-c"])
    assert config == original
