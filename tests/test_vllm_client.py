from __future__ import annotations

import pytest

from pi_sync.vllm_client import VLLMClient, VLLMConnectionError, VLLMParseError


def models_response(*ids) -> dict:
    return {"object": "list", "data": [{"id": mid, "object": "model"} for mid in ids]}


def test_get_model_ids_returns_server_ids():
    client = VLLMClient(_http_get=lambda _url, _timeout: models_response("a", "b"))
    assert client.get_model_ids() == ["a", "b"]


def test_models_url_uses_base_url():
    calls = []

    def get(url, timeout):
        calls.append((url, timeout))
        return models_response("m")

    VLLMClient(base_url="http://host:8080/v1/", timeout=12, _http_get=get).get_model_ids()
    assert calls == [("http://host:8080/v1/models", 12)]


def test_missing_data_raises_parse_error():
    client = VLLMClient(_http_get=lambda _url, _timeout: {"object": "list"})
    with pytest.raises(VLLMParseError):
        client.get_model_ids()


def test_connection_error_propagates():
    client = VLLMClient(_http_get=lambda _url, _timeout: (_ for _ in ()).throw(VLLMConnectionError("nope")))
    with pytest.raises(VLLMConnectionError, match="nope"):
        client.get_model_ids()
