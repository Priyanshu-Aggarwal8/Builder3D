# System Architecture Overview
The system is a **cloud-native microservices platform**. Users interact via an Angular Single-Page App (SPA) hosted on CDN/CloudFront. All API calls go through a central API Gateway (e.g. AWS API Gateway or NGINX) for routing, authentication, and throttling. The backend is composed of *multiple FastAPI services* (Docker containers, e.g. on AWS ECS/EKS), including:  
- **Auth Service:** Manages users, roles, and JWT issuance. Uses OAuth2 flows + JWT tokens. Stores hashed passwords in DB (bcrypt).  
- **Project Service:** Handles project creation, storage of requirements (plot size, rooms, floors). CRUD operations on projects.  
- **Design Engine Service:** Core AI logic. Takes project requirements and generates floor plans (2D/3D), structural elements, and initial BIM model. Initially rule-based engine; later augmented by ML.  
- **Validation Service:** Performs structural simulation and code compliance checks (e.g. load calculations, building codes).  
- **AR Service:** Prepares data for AR. Provides endpoints for mobile/AR apps (e.g. anchor points for on-site overlay).  
- **Worker/Queue Services:** Asynchronous tasks (e.g. heavy compute design jobs) via message queue (RabbitMQ/Kafka).  
- **File Service:** Manages storage of 3D models, PDFs, CAD files (in S3 or Blob).  
All services are **stateless** and use a central PostgreSQL (with SQLAlchemy) for persistent data, plus Redis for caching. They use a shared **BIM data model** (IFC/JSON) for interoperability. File uploads go to S3 (e.g. glTF/OBJ models). System-wide logging and metrics feed into CloudWatch/Prometheus.  

Security is enforced at each layer: HTTPS/TLS for transport, input schemas (Pydantic) for validation, and RBAC checks in services (roles: Admin, Architect, Contractor, Worker). Secrets (DB credentials, JWT keys) are in AWS Secrets Manager (or env vars encrypted).  
The architecture ensures **loose coupling and high cohesion**: each service has a single responsibility, communicates via REST/gRPC or queue, and can be deployed or scaled independently. This follows the AWS/EKS reference architecture patterns for microservices.  

```mermaid
graph LR
    UI[Angular Frontend] -->|REST API| GW[API Gateway]
    GW --> Auth[Auth Service (FastAPI)]
    GW --> ProjectS[Project Service]
    GW --> Design[Design Engine Service]
    GW --> Validation[Validation Service]
    GW --> ARSvc[AR Guidance Service]
    Design --> |"Queue:DesignJobs"| MQ[(RabbitMQ)]
    Validation --> |"Queue:ValidationJobs"| MQ
    ARSvc --> |"Queue:ARJobs"| MQ
    Auth --> |"DB"| DB[(PostgreSQL)]
    ProjectS --> DB
    Design --> DB
    Validation --> DB
    ARSvc --> DB
    MQ --> WorkerA[Design Worker]
    MQ --> WorkerB[Validation Worker]
    MQ --> WorkerC[AR Worker]
    WorkerA --> S3[(S3 Models)]
    WorkerB --> S3
    WorkerC --> S3
    GW --> CI[CI/CD Pipeline (GitHub Actions)]
    GW --> Observability[(Monitoring & Logging)]
    Observability --> Grafana[(Grafana)]
    Observability --> Prometheus[(Prometheus)]
```
