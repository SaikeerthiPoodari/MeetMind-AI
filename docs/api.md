# API surface

- `GET /api/health` — service and demo status.
- `POST /api/auth/register`, `POST /api/auth/login` — JWT authentication.
- `GET /api/meetings`, `GET /api/meetings/{id}` — meeting intelligence.
- `POST /api/meetings/{id}/upload` — server-side MIME and size validation.
- `POST /api/meetings/{id}/process` — processing orchestration boundary.
- `POST /api/meetings/{id}/ask` — grounded meeting Q&A with evidence.
- `GET /api/actions` — global action center data.

The OpenAPI document is available from FastAPI at `/openapi.json`.
