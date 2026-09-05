# Atlas SDK

Thin HTTP client for the Atlas control-plane API.

`atlas-sdk` is the stable Python SDK used by the CLI and other Atlas
tooling. It contains no business logic — just client DTOs, request/response
models, and error types over `httpx`.

**Note:** the public PyPI project named `atlas-sdk` (by `atlassistant`) is an
unrelated package. This distribution is published from this repository only
under a private index / as part of the `atlas-cli` bundle.

## Usage

```python
from atlas_sdk.client import AtlasClient

client = AtlasClient(base_url="http://localhost:8000", token="...")
health = client.health_summary()
print(health.version)
```

## Requirements

- Python 3.11+
- `httpx>=0.28.1`
- `pydantic[email]>=2.0.0`

## Development

```bash
pip install -e ./sdk/python
```

## License

Copyright (c) 2026. All rights reserved.