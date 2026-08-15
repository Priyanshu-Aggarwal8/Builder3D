# Phase 1 Testing Outline
- **Unit Tests:**  
  - Test `ProjectService` validation logic (e.g. invalid plot_size raises).  
  - Test `ProjectRepository` methods against a SQLite in-memory DB (create/read).  
  - Angular: test that `ProjectService` calls HttpClient correctly (use HttpClientTestingModule).  
- **Integration Tests:**  
  - FastAPI TestClient: test the `/projects` endpoint end-to-end (uses a test database).  
- **Acceptance Tests:**  
  - Postman or Cypress: simulate creating a project and checking the returned layout.  
All tests should pass before any merge to `main`. Use CI to enforce.
