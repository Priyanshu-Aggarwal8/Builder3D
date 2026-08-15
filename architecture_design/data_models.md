# Data Models (ER Diagrams)
The key data entities for Phase 1 are **User**, **Project**, **Room**. Future phases will add entities like `FloorPlan`, `DesignResult`, `MaterialList`, etc. Example ER diagram:  
```mermaid
erDiagram
    USER {
        int id PK
        string name
        string email
        string password_hash
    }
    PROJECT {
        int id PK
        int user_id FK
        float plot_size
        int floors
        string rooms_JSON
        string status
    }
    ROOM {
        int id PK
        int project_id FK
        string name
        float area
    }
    USER ||--o{ PROJECT : owns
    PROJECT ||--o{ ROOM : contains
```  
- **User**: authentication data.  
- **Project**: stores the requirements and status. `rooms_JSON` (or a related table) holds a list of requested rooms.  
- **Room**: (for MVP) optionally store each room’s area as computed.  
Future tables: `Design` (3D model metadata), `Task` (status of async jobs), etc. All IDs are surrogate keys. Relationships use foreign keys (e.g. PROJECT.user_id→USER.id). Use SQLAlchemy/SQLModel with Pydantic schemas for validation.
