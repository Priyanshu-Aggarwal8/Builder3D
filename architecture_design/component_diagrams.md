# Component Diagrams
Below is a view of key components and data flows:  
```mermaid
graph TD
    subgraph Frontend
        UI[Angular SPA]
    end
    subgraph BackEnd
        APIGW[API Gateway]
        AuthSvc[Auth Service]
        ProjSvc[Project Service]
        DesignSvc[Design Service]
        ValSvc[Validation Service]
        ARSvc[AR Service]
    end
    subgraph DataLayer
        DB[(PostgreSQL)]
        MQ[(Message Queue)]
        Storage[(Object Storage (S3))]
    end

    UI --> APIGW
    APIGW --> AuthSvc
    APIGW --> ProjSvc
    APIGW --> DesignSvc
    APIGW --> ValSvc
    APIGW --> ARSvc
    AuthSvc --> DB
    ProjSvc --> DB
    DesignSvc --> DB
    ValSvc --> DB
    ARSvc --> DB
    DesignSvc --> MQ
    ValSvc --> MQ
    ARSvc --> MQ
    MQ --> DesignSvc
    MQ --> ValSvc
    MQ --> ARSvc
    DesignSvc --> Storage
    ARSvc --> Storage
```  
Each microservice is its own container/pod. DB is a managed RDS instance. MQ is a durable queue (RabbitMQ or managed Kafka). Storage is S3 (AWS) or Google Cloud Storage.
