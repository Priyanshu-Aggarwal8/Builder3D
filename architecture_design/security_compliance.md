# Security & Compliance Standards
The platform must adhere to industry best practices and legal standards:  
- **Authentication/Authorization:** JWT-based auth with short-lived tokens, refresh tokens. Roles (RBAC) enforced in services.  
- **Input Validation:** All inputs use Pydantic models; reject invalid data. Protect against injection, XSS (sanitize any user HTML).  
- **Encryption:** TLS 1.3 everywhere. DB encryption at rest (RDS encryption), S3 encryption.  
- **Secrets Management:** Use AWS Secrets Manager or environment variables, never hardcode keys. Rotate keys regularly.  
- **Logging/Audit:** Log all admin actions and security events (login attempts, config changes) to immutable log store.  
- **Dependency Scanning:** Integrate Snyk or npm audit in CI. Follow OWASP ASVS guidelines for API security.  
- **Compliance:** If targeting enterprise, prepare for SOC 2 (security controls, logging). If handling personal data, GDPR/CCPA compliance (encryption, data deletion). For BIM data, align with ISO 19650 data management principles.  
- **Network:** In Kubernetes, use network policies and security groups for isolation. Use IAM roles for AWS resources.  
Security and compliance checklists are included in each phase (see Phases section). All code and infra changes must pass security reviews.
