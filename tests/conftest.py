"""Shared fixtures and helpers for pi-sync tests."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List

import pytest


class _MockVLLMHandler(BaseHTTPRequestHandler):
    models: List[str] = []
    fail_with: int = 0

    def do_GET(self):
        if self.fail_with:
            self.send_response(self.fail_with)
            self.end_headers()
            return

        if self.path == "/v1/models":
            body = json.dumps(
                {
                    "object": "list",
                    "data": [
                        {"id": m, "object": "model", "owned_by": "vllm"}
                        for m in self.models
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_):
        pass


class MockVLLMServer:
    def __init__(self, models: List[str], fail_with: int = 0):
        _MockVLLMHandler.models = models
        _MockVLLMHandler.fail_with = fail_with
        self._server = HTTPServer(("127.0.0.1", 0), _MockVLLMHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def shutdown(self):
        self._server.shutdown()


@pytest.fixture()
def mock_server():
    servers = []

    def factory(models: List[str], fail_with: int = 0) -> MockVLLMServer:
        srv = MockVLLMServer(models, fail_with=fail_with)
        servers.append(srv)
        return srv

    yield factory

    for srv in servers:
        srv.shutdown()


SAMPLE_CONFIG = {
    "providers": {
        "llama-cpp": {
            "baseUrl": "http://localhost:8080/v1",
            "api": "openai-completions",
            "apiKey": "llama",
            "compat": {
                "supportsDeveloperRole": False,
                "supportsReasoningEffort": False,
            },
            "models": [
                {
                    "id": "org/model-a",
                    "name": "Model A",
                    "input": ["text"],
                    "contextWindow": 32768,
                    "maxTokens": 8192,
                },
                {
                    "id": "org/model-b",
                    "name": "Model B",
                    "input": ["text"],
                    "contextWindow": 32768,
                    "maxTokens": 8192,
                },
            ],
        }
    }
}


SAMPLE_JSONC = """\
{
  // Pi custom model providers
  "providers": {
    "llama-cpp": {
      "baseUrl": "http://localhost:8080/v1",
      "api": "openai-completions",
      "apiKey": "llama",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false,
      },
      "models": [
        { "id": "org/model-a", "name": "Model A", "input": ["text"], "contextWindow": 32768, "maxTokens": 8192 },
        { "id": "org/model-b", "name": "Model B", "input": ["text"], "contextWindow": 32768, "maxTokens": 8192 },
      ]
    }
  }
}
"""
