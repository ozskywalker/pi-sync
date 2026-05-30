"""Read, parse, update, and write Pi models.json config files."""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# JSONC parsing
# ---------------------------------------------------------------------------

def _strip_jsonc_comments(text: str) -> str:
    """Remove // and /* */ comments from JSONC text, leaving string literals intact."""
    result: List[str] = []
    i = 0
    n = len(text)
    in_string = False

    while i < n:
        c = text[i]
        if in_string:
            if c == "\\" and i + 1 < n:
                result.append(c)
                result.append(text[i + 1])
                i += 2
            elif c == '"':
                in_string = False
                result.append(c)
                i += 1
            else:
                result.append(c)
                i += 1
        else:
            if c == '"':
                in_string = True
                result.append(c)
                i += 1
            elif c == "/" and i + 1 < n and text[i + 1] == "/":
                # Single-line comment: skip to end of line
                while i < n and text[i] != "\n":
                    i += 1
            elif c == "/" and i + 1 < n and text[i + 1] == "*":
                # Block comment: skip to */
                i += 2
                while i < n - 1:
                    if text[i] == "*" and text[i + 1] == "/":
                        i += 2
                        break
                    i += 1
                else:
                    i = n  # unterminated block comment - consume to EOF
            else:
                result.append(c)
                i += 1

    return "".join(result)


def _strip_trailing_commas(text: str) -> str:
    """Remove trailing commas before } or ] (valid JSONC, invalid JSON)."""
    return re.sub(r",(\s*[}\]])", r"\1", text)


def parse_jsonc(text: str) -> dict:
    """Parse a JSONC string (JSON with comments and trailing commas) into a dict."""
    cleaned = _strip_jsonc_comments(text)
    cleaned = _strip_trailing_commas(cleaned)
    return json.loads(cleaned)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_PROVIDER_ID = "llama-cpp"
DEFAULT_BASE_URL = "http://localhost:8080/v1"
DEFAULT_API_KEY = "llama"
DEFAULT_API = "openai-completions"
DEFAULT_CONTEXT_WINDOW = 32768
DEFAULT_MAX_TOKENS = 8192
DEFAULT_MODEL_ID = "qwen3-coder-local"
DEFAULT_MODEL_NAME = "Qwen local via llama-server"


def default_config(base_url: str = DEFAULT_BASE_URL) -> dict:
    """Return a valid Pi models.json config for a local OpenAI-compatible server."""
    return {
        "providers": {
            DEFAULT_PROVIDER_ID: {
                "baseUrl": base_url,
                "api": DEFAULT_API,
                "apiKey": DEFAULT_API_KEY,
                "compat": {
                    "supportsDeveloperRole": False,
                    "supportsReasoningEffort": False,
                },
                "models": [
                    {
                        "id": DEFAULT_MODEL_ID,
                        "name": DEFAULT_MODEL_NAME,
                        "input": ["text"],
                        "contextWindow": DEFAULT_CONTEXT_WINDOW,
                        "maxTokens": DEFAULT_MAX_TOKENS,
                    }
                ],
            }
        }
    }


def _agent_dir() -> Path:
    configured = os.environ.get("PI_CODING_AGENT_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".pi" / "agent"


def find_config_path() -> Optional[Path]:
    """Return Pi's models.json path."""
    return _agent_dir() / "models.json"


# ---------------------------------------------------------------------------
# Config I/O
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    """Load and parse a Pi models.json file."""
    text = path.read_text(encoding="utf-8")
    return parse_jsonc(text)


def save_config(path: Path, config: dict) -> None:
    """Write config dict to disk as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Config manipulation
# ---------------------------------------------------------------------------

def generate_display_name(model_id: str) -> str:
    """Derive a human-readable display name from a model ID."""
    # Strip org prefix (e.g., "Qwen/Qwen3-27B" -> "Qwen3-27B")
    return model_id.split("/")[-1] if "/" in model_id else model_id


def find_provider_by_url(config: dict, base_url: str) -> Optional[str]:
    """Return the provider ID whose baseUrl matches, or None."""
    target = base_url.rstrip("/")
    for provider_id, provider in config.get("providers", {}).items():
        existing = provider.get("baseUrl", "").rstrip("/")
        if existing == target:
            return provider_id
    return None


def update_provider_models(
    config: dict,
    provider_id: str,
    model_ids: List[str],
    base_url: Optional[str] = None,
    update_active_model: bool = True,
) -> Tuple[dict, List[str], List[str]]:
    """
    Update a Pi provider's models list in the config dict.

    Args:
        config:              The existing config dict (not mutated - a deep copy is returned).
        provider_id:         Which provider entry to update.
        model_ids:           The full list of model IDs now served by the server.
        base_url:            If set, also update the provider's baseUrl.
        update_active_model: Kept for CLI compatibility; Pi does not store an active
                             model in models.json.

    Returns:
        (updated_config, added_ids, removed_ids)
    """
    config = copy.deepcopy(config)

    providers: Dict = config.setdefault("providers", {})

    if provider_id not in providers:
        providers[provider_id] = default_config()["providers"][DEFAULT_PROVIDER_ID]

    provider = providers[provider_id]

    if base_url is not None:
        provider["baseUrl"] = base_url

    provider.setdefault("api", DEFAULT_API)
    provider.setdefault("apiKey", DEFAULT_API_KEY)
    provider.setdefault(
        "compat",
        {"supportsDeveloperRole": False, "supportsReasoningEffort": False},
    )

    existing_models = {
        model.get("id"): model
        for model in provider.get("models", [])
        if isinstance(model, dict) and model.get("id")
    }
    existing_ids = set(existing_models)
    new_ids = set(model_ids)
    added = sorted(new_ids - existing_ids)
    removed = sorted(existing_ids - new_ids)

    # Rebuild models list: preserve existing entries, add new ones with local defaults.
    new_models: List[dict] = []
    for mid in model_ids:
        if mid in existing_models:
            new_models.append(existing_models[mid])
        else:
            new_models.append(
                {
                    "id": mid,
                    "name": generate_display_name(mid),
                    "input": ["text"],
                    "contextWindow": DEFAULT_CONTEXT_WINDOW,
                    "maxTokens": DEFAULT_MAX_TOKENS,
                }
            )
    provider["models"] = new_models

    return config, added, removed
