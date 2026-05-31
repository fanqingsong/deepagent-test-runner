# Configuration

## Environment Variables

**File:** `platform/.env`

### Required Variables

- `LLM_API_KEY`: Required for GLM LLM access
- `LLM_BASE_URL`: LLM API endpoint (default: `https://open.bigmodel.cn/api/paas/v4`)
- `LLM_MODEL`: Model name (default: `glm-4-plus`)
- `POSTGRES_PASSWORD`: Database credentials
- `SECRET_KEY`: JWT signing key

## API Port Mappings

| Port | Service |
|------|---------|
| 8080 | Nginx reverse proxy (routes to backend services) |
| 8011 | Unified Backend (FastAPI) |
| 5173 | Vite dev server (for React frontend hot-reload) |
| 5433 | PostgreSQL (external access) |
| 6380 | Redis (external access) |
