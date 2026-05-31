# Dashboard Service

Provides test analytics dashboard and test management UI.

## Development

### Backend Development
```bash
npm start
```
Server runs on port 8003.

### Frontend Development
```bash
cd frontend
npm run dev
```
React dev server runs on port 5173.

### Full Stack Development
```bash
npm run dev:full
```
Runs both backend and frontend concurrently.

## Building

### Production Build
```bash
# Build frontend only
cd frontend
npm run build

# Build Docker image (includes frontend build)
docker-compose build dashboard-service
```

## Features

- **Test List View:** View all tests with search and tag filtering
- **Test Creation:** Create new tests with steps via web UI
- **Test Execution:** Trigger test runs directly from the UI
- **Analytics Dashboard:** View test metrics and trends

## API Endpoints

- `GET /health` - Health check
- `GET /api/dashboard` - Dashboard summary
- `GET /api/test-runs` - Recent test runs
- And more analytics endpoints...

See [API Documentation](../../README.md#api-endpoints) for full API reference.
