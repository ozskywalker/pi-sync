# pi-sync

Small stdlib-only Python package that syncs Pi coding agent custom models from an OpenAI-compatible `/v1/models` endpoint.

Relevant files:

- `pi_sync/cli.py`: CLI and `install` wrapper.
- `pi_sync/config.py`: JSONC parsing, default Pi `models.json`, and provider/model update logic.
- `pi_sync/vllm_client.py`: minimal `/v1/models` client.
- `tests/`: pytest coverage for config, wrapper, HTTP client, and end-to-end sync.

Run tests with:

```bash
python -m pytest
```
