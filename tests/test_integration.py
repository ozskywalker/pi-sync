from __future__ import annotations

import json

import pytest

from pi_sync.cli import main
from pi_sync.config import DEFAULT_PROVIDER_ID, default_config, load_config
from tests.conftest import SAMPLE_CONFIG


def model_ids(config: dict, provider: str = DEFAULT_PROVIDER_ID) -> list[str]:
    return [m["id"] for m in config["providers"][provider]["models"]]


def model_by_id(config: dict, model_id: str, provider: str = DEFAULT_PROVIDER_ID) -> dict:
    return next(m for m in config["providers"][provider]["models"] if m["id"] == model_id)


def test_sync_creates_missing_models_json(tmp_path, mock_server):
    cfg = tmp_path / "agent" / "models.json"
    srv = mock_server(["org/model-a", "org/model-b"])

    rc = main(["--config", str(cfg), "--host", "127.0.0.1", "--port", str(srv.port)])

    assert rc == 0
    updated = load_config(cfg)
    assert model_ids(updated) == ["org/model-a", "org/model-b"]
    assert updated["providers"][DEFAULT_PROVIDER_ID]["api"] == "openai-completions"
    assert updated["providers"][DEFAULT_PROVIDER_ID]["apiKey"] == "llama"
    assert updated["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == srv.base_url


def test_missing_config_is_created_even_when_server_down(tmp_path):
    cfg = tmp_path / "agent" / "models.json"

    with pytest.raises(SystemExit):
        main(["--config", str(cfg), "--host", "127.0.0.1", "--port", "1"])

    updated = load_config(cfg)
    assert updated["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == "http://127.0.0.1:1/v1"


def test_sync_preserves_custom_display_names(tmp_path, mock_server):
    cfg = tmp_path / "models.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")
    srv = mock_server(["org/model-a", "org/model-c"])

    main(["--config", str(cfg), "--host", "127.0.0.1", "--port", str(srv.port)])

    updated = load_config(cfg)
    assert model_by_id(updated, "org/model-a")["name"] == "Model A"
    assert model_by_id(updated, "org/model-c")["name"] == "model-c"
    assert "org/model-b" not in model_ids(updated)


def test_sync_uses_existing_base_url_when_no_host_port(tmp_path, mock_server):
    srv = mock_server(["org/model-x"])
    cfg = tmp_path / "models.json"
    config = default_config(srv.base_url)
    cfg.write_text(json.dumps(config), encoding="utf-8")

    rc = main(["--config", str(cfg)])

    assert rc == 0
    updated = load_config(cfg)
    assert model_ids(updated) == ["org/model-x"]
    assert updated["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == srv.base_url


def test_env_host_port_used_when_no_cli_target(tmp_path, mock_server, monkeypatch):
    cfg = tmp_path / "models.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")
    srv = mock_server(["org/env-model"])
    monkeypatch.setenv("LLAMA_ARG_HOST", "127.0.0.1")
    monkeypatch.setenv("LLAMA_ARG_PORT", str(srv.port))

    rc = main(["--config", str(cfg)])

    assert rc == 0
    updated = load_config(cfg)
    assert "org/env-model" in model_ids(updated)
    assert updated["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == srv.base_url


def test_cli_target_overrides_env_target(tmp_path, mock_server, monkeypatch):
    cfg = tmp_path / "models.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")
    srv = mock_server(["org/cli-model"])
    monkeypatch.setenv("LLAMA_ARG_HOST", "127.0.0.1")
    monkeypatch.setenv("LLAMA_ARG_PORT", "1")

    rc = main([
        "--config", str(cfg),
        "--host", "127.0.0.1", "--port", str(srv.port),
    ])

    assert rc == 0
    updated = load_config(cfg)
    assert "org/cli-model" in model_ids(updated)
    assert updated["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == srv.base_url


def test_invalid_env_port_exits_nonzero(tmp_path, monkeypatch):
    cfg = tmp_path / "models.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")
    monkeypatch.setenv("LLAMA_ARG_PORT", "not-a-port")

    with pytest.raises(SystemExit) as exc_info:
        main(["--config", str(cfg)])

    assert exc_info.value.code != 0


def test_no_url_update_preserves_existing_base_url(tmp_path, mock_server):
    srv = mock_server(["org/model-a"])
    cfg = tmp_path / "models.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")

    main(["--config", str(cfg), "--host", "127.0.0.1", "--port", str(srv.port), "--no-url-update"])

    updated = load_config(cfg)
    assert updated["providers"][DEFAULT_PROVIDER_ID]["baseUrl"] == "http://localhost:8080/v1"


def test_dry_run_does_not_write(tmp_path, mock_server):
    srv = mock_server(["org/new"])
    cfg = tmp_path / "models.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")
    original = cfg.read_text()

    rc = main(["--config", str(cfg), "--host", "127.0.0.1", "--port", str(srv.port), "--dry-run"])

    assert rc == 0
    assert cfg.read_text() == original


def test_multiple_providers_requires_selection(tmp_path, mock_server):
    srv = mock_server(["org/model-a"])
    cfg = tmp_path / "models.json"
    cfg.write_text(
        json.dumps(
            {
                "providers": {
                    "a": {"baseUrl": "http://a/v1", "api": "openai-completions", "apiKey": "x", "models": []},
                    "b": {"baseUrl": "http://b/v1", "api": "openai-completions", "apiKey": "x", "models": []},
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        main(["--config", str(cfg), "--host", "127.0.0.1", "--port", str(srv.port)])


def test_empty_model_list_no_write(tmp_path, mock_server):
    srv = mock_server([])
    cfg = tmp_path / "models.json"
    cfg.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")
    original = cfg.read_text()

    rc = main(["--config", str(cfg), "--host", "127.0.0.1", "--port", str(srv.port)])

    assert rc == 0
    assert cfg.read_text() == original
