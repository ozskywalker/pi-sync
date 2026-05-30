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

`pi-sync` also respects llama.cpp's server target environment variables:

```bash
LLAMA_ARG_HOST=127.0.0.1 LLAMA_ARG_PORT=8080 pi-sync
```

Target precedence is:

| Source | Server queried | `baseUrl` in config |
|---|---|---|
| `pi-sync` | Existing `baseUrl` (fallback: `localhost:8080`) | **Unchanged** |
| `LLAMA_ARG_HOST=X pi-sync` | `http://X:8080/v1` | Updated |
| `LLAMA_ARG_HOST=X LLAMA_ARG_PORT=9000 pi-sync` | `http://X:9000/v1` | Updated |
| `pi-sync --host X` | `http://X:8080/v1` | Updated |
| `pi-sync --host X --no-url-update` | `http://X:8080/v1` | **Unchanged** |

CLI `--host`/`--port` values override `LLAMA_ARG_HOST`/`LLAMA_ARG_PORT`.

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
      "baseUrl": "http://localhost:8080/v1",
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

| Flag | Default | Description |
|---|---|---|
| `--host HOST` | env, config, else localhost | vLLM server hostname |
| `--port PORT` | env, config, else 8080 | vLLM server port |
| `--provider ID` | auto-detect | Provider key to update |
| `--config PATH` | auto-detect | Path to Pi `models.json` |
| `--dry-run` | off | Show changes without writing |
| `--no-url-update` | off | Query the target without updating stored `baseUrl` |
| `--timeout SECONDS` | 10 | HTTP request timeout |

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```
