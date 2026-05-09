# Observability Troubleshooting

## Issue: No metrics in Prometheus

**Symptoms**: `/metrics` endpoint returns 404, Prometheus targets show DOWN

**Solutions**:
1. Check if Prometheus enabled: `echo $PROMETHEUS_ENABLED`
2. Verify middleware loaded: Check startup logs for "Prometheus metrics enabled"
3. Check port conflicts: Ensure port 9090 not already in use
4. Verify scrape config: `kubectl get configmap prometheus-config -n observability -o yaml`

## Issue: Logs not appearing in Loki

**Symptoms**: Grafana Loki datasource shows "No data"

**Solutions**:
1. Check Promtail logs: `kubectl logs -n observability -l app=promtail`
2. Verify log format: Ensure `LOG_FORMAT=json` in backend .env
3. Check Loki connection: Promtail logs should show "Connected to Loki"
4. Verify labels: Use `{namespace="claude-test-runner"}` query in Loki

## Issue: No traces in Jaeger

**Symptoms**: Jaeger UI shows "No traces"

**Solutions**:
1. Check if tracing enabled: `echo $JAEGER_ENABLED`
2. Verify agent connection: Backend logs should show "Jaeger agent at jaeger:6831"
3. Check sampling rate: Ensure `TRACE_SAMPLE_RATE > 0` (e.g., 1.0 for dev, 0.1 for prod)
4. Make API request: Traces only appear after requests are made
5. Check time range: Jaeger UI defaults to "Last hour", adjust if needed

## Issue: High memory usage in Grafana

**Symptoms**: Grafana pod OOMKilled

**Solutions**:
1. Increase memory limit: `kubectl edit deployment grafana -n observability`
2. Reduce dashboard refresh rate: Change from 5s to 30s
3. Reduce time range in queries: Use shorter time ranges
4. Clear cache: Grafana UI > Configuration > Users > Clear cache

## Issue: Correlation ID missing in logs

**Symptoms**: Logs don't have `correlation_id` field

**Solutions**:
1. Verify logging middleware loaded: Check startup logs for "Structured logging enabled"
2. Check middleware order: `setup_observability()` must be called before `app.add_middleware(CORSMiddleware)`
3. Test manually: Make request with `curl -H "X-Correlation-ID: test-123" http://localhost:8001/api/v1/health`

## Issue: Dependencies not found

**Symptoms**: ImportError when starting backend

**Solutions**:
1. Rebuild Docker image: `docker-compose build backend`
2. Install dependencies: `pip install -r requirements.txt`
3. Verify package versions in requirements.txt are compatible
