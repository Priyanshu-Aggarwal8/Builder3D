# Monitoring & Observability Plan
- **Metrics:** Use Prometheus or CloudWatch to collect metrics (CPU, memory, request rates, error rates) from all services. Instrument FastAPI with Prometheus client (metrics: request duration, error counts).  
- **Logs:** Centralize logs via CloudWatch/ELK stack. All services should log structured JSON (include request IDs). Retain logs per compliance rules.  
- **Tracing:** (Phase 2+) Integrate OpenTelemetry for distributed tracing (Jaeger or AWS X-Ray) to trace calls across microservices.  
- **Alerts:** Set up alerts on key metrics (e.g. error% > 5%, high latency) with PagerDuty or AWS SNS.  
- **Dashboards:** Build Grafana dashboards for system health (requests per second, queue depth, design job times) and business metrics (projects created per day).  
- **Health checks:** Each service exposes `/health` for readiness. Kubernetes liveness probes kill unhealthy pods.  
Observability is mandatory from Phase 1 to catch issues early. E.g. log every failed input validation and track them (per OWASP recommendation).
