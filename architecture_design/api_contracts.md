# API Contracts
Define clear HTTP interfaces. Example endpoints (Phase 1):  
- **POST /projects** – Create a new project.  
  - *Request JSON:* `{ "plot_size": number, "rooms": [string], "floors": number }`  
  - *Response JSON:* `{ "id": 123, "plot_size": 1000, "floors": 2, "rooms": ["Bedroom","Kitchen"] }` or error.  
- **GET /projects/{id}** – Retrieve project details and generated layout.  
  - *Response:* `{ "id": 123, "plot_size": 1000, "floors": 2, "rooms": ["Bedroom","Kitchen"], "layout": [ ... ] }`.  
- **GET /projects** – List user’s projects (supports pagination).  
- **POST /auth/signup, /auth/login** – User management (if included in Phase 1).  
All APIs accept and return JSON. Use OpenAPI (Swagger) for docs (FastAPI auto-generates it). Include proper HTTP codes (201 Created, 400 Bad Request on validation errors). Example:  
```json
// Request to create project
{
  "plot_size": 1200,
  "rooms": ["bedroom", "kitchen", "bathroom"],
  "floors": 1
}
// Response
{
  "id": 101,
  "plot_size": 1200,
  "floors": 1,
  "rooms": ["bedroom", "kitchen", "bathroom"],
  "layout": [...]
}
```  

Use JWT in Authorization headers for protected endpoints (e.g. `Authorization: Bearer <token>`). All inputs must be validated via Pydantic schemas (no implicit trust). The API layer should handle exceptions and return structured errors (e.g. `{"status":"error","message":"Invalid rooms list","code":400}`).
