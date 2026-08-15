# Phase 1 Code Structure (Example)
Demonstrating separation of concerns:  
```
code/
├── backend/
│   ├── app/
│   │   ├── api/               # FastAPI routers/controllers
│   │   ├── services/          # business logic
│   │   ├── repositories/      # database access
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── core/              # config, security
│   │   └── main.py
└── requirements.txt
├── frontend/
│   ├── src/app/
│   │   ├── core/             # shared services
│   │   ├── shared/           # shared components, pipes
│   │   ├── features/
│   │   │   └── project/      # components and services for projects
│   │   └── app.module.ts
│   └── angular.json
```  
Each layer is independent. For example, repositories **only** interact with the DB and never contain presentation logic, following FastAPI’s multi-file guide.
