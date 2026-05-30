# pi-sync

Keep Pi coding agent's `models.json` in sync with your local vLLM or llama.cpp `llama-server`.

`pi-sync` queries `GET /v1/models`, updates `~/.pi/agent/models.json`, and preserves existing model metadata for IDs that are still served. If `models.json` does not exist, it creates a local `llama-cpp` provider using the OpenAI-compatible completions API.

## Install

```bash
pip install -e .
```

## Usage

Sync against the URL already in `models.json`, or create the default local config:

```bash
pi-sync
```

Point at a specific server and update the stored URL:

```bash
pi-sync --host 127.0.0.1 --port 8080
```

Preview changes without writing:

```bash
pi-sync --dry-run
```

## Auto-sync on every Pi launch

Install the wrapper once:

```bash
pi-sync install
```

This writes `~/.local/bin/pi`, which runs `pi-sync` silently and then execs the real `pi` binary. Make sure `~/.local/bin` appears earlier in `PATH` than the real Pi binary.

## Default Config

When creating a new config, `pi-sync` starts with:

```json
{
  "providers": {
    "llama-cpp": {
      "baseUrl": "http://127.0.0.1:8080/v1",
      "api": "openai-completions",
      "apiKey": "llama",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "qwen3-coder-local",
          "name": "Qwen local via llama-server",
          "input": ["text"],
          "contextWindow": 32768,
          "maxTokens": 8192
        }
      ]
    }
  }
}
```

## Options

```text
pi-sync [--host HOST] [--port PORT] [--provider ID] [--config PATH]
        [--dry-run] [--no-url-update] [--timeout SECONDS]
```

The default config path is `$PI_CODING_AGENT_DIR/models.json`, or `~/.pi/agent/models.json` when `PI_CODING_AGENT_DIR` is unset.

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```
