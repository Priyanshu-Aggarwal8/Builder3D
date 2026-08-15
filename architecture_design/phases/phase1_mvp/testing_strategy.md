# Phase 1 Testing Strategy
- **Unit Tests:** Backend (PyTest) for services/repositories; Frontend (Karma/Jasmine) for components.  
- **Integration Tests:** Test API endpoints with TestClient (FastAPI) and in-memory DB (e.g. SQLite).  
- **End-to-End:** Simulate user flow: create project, get layout.  
- **Coverage:** Aim >80% code coverage on backend logic.
