# Architecture Diagrams
The diagrams below show the system structure and data flows. The microservices are organized around domain boundaries (Project management, Design, AR, etc.), as recommended in cloud microservices patterns.  

**Figure 1. System Overview:** shows the high-level services and interactions (reproduced above).  

**Mermaid Sequence:** The startup sequence and data flow for a new project:  
```mermaid
sequenceDiagram
  participant U as User (Angular UI)
  participant GW as API Gateway
  participant AS as Auth Service
  participant PS as Project Service
  participant DE as Design Engine
  participant DB as PostgreSQL

  U->>GW: POST /projects (user inputs)
  GW->>AS: Auth check (JWT)
  AS-->>GW: [OK]
  GW->>PS: CreateProject(data)
  PS->>DB: INSERT project
  DB-->>PS: [new project id]
  PS-->>GW: ProjectID
  GW-->>DE: Submit design job (project requirements)
  DE->>MQ: Publish design task
  Note right of MQ: Asynchronous design processing
  MQ->>WorkerA: Pull design task
  WorkerA->>DE: Execute design algorithms
  DE-->>WorkerA: floor plans, materials, etc.
  WorkerA->>S3: Upload 3D model
  WorkerA->>DB: Save design results
  WorkerA-->>MQ: Publish completion message
  MQ->>PS: Notify completion
  PS-->>U: Return design summary (via Gateway)
```  

These diagrams ensure *everything* is well-defined. All arrows and steps must be formally implemented in the APIs and services.
