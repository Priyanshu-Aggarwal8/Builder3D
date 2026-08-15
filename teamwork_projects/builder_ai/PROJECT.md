# Project: Builder AI Phase 1

## Architecture
- **Backend**: FastAPI (Python 3.11+) REST API with Uvicorn, SQLAlchemy ORM, Pydantic schemas, and SQLite database.
- **Frontend**: React + Vite + Three.js WebGL 3D Canvas with OrbitControls, TransformControls, Layer Toggle Controls, and Property Inspector.
- **Testing**: PyTest backend test suite (unit + API integration) + E2E test harness for full-stack integration and visual layer/edit verification.

## Code Layout
```
teamwork_projects/builder_ai/
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   └── project.py
│   │   ├── schemas/
│   │   │   └── project.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── projects.py
│   │   │       └── models.py
│   │   └── services/
│   │       └── model_service.py
│   └── tests/
│       ├── conftest.py
│       ├── test_models.py
│       └── test_api.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── components/
│       │   ├── Viewport.jsx
│       │   ├── LayerControls.jsx
│       │   └── PropertyInspector.jsx
│       └── services/
│           └── api.js
└── tests_e2e/
    ├── e2e_test_runner.py
    └── test_suite.py
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Backend Scaffolding & Database | FastAPI server setup, SQLite DB, SQLAlchemy models, Pydantic validation | M1 | Survey |
| 2 | Project CRUD APIs | REST API endpoints (`POST`, `GET`, `DELETE` `/api/projects`) | M1 | Survey |
| 3 | 3D Model API | REST API endpoint `GET /api/projects/{id}/model` serving structured JSON | M1 | Survey |
| 4 | Real-Time Edit API | REST API endpoint `PATCH /api/projects/{id}/elements/{element_id}` | M1 | Survey |
| 5 | Frontend SPA Scaffolding | React + Vite setup, package.json, Three.js dependencies, app layout | M2 | Survey |
| 6 | WebGL 3D Canvas | Three.js scene, camera, ambient/directional lights, OrbitControls, grid | M2 | Survey |
| 7 | Multi-Layer Group Renderer | Render Structural, Electrical, and Plumbing layers with distinct materials | M2 | Survey |
| 8 | Layer Toggle UI Controls | Interactive UI switches/checkboxes to independently show/hide layers | M2 | Survey |
| 9 | 3D Raycast Element Selection | Pointer click object selection via Raycaster and visual selection bounding box | M3 | Survey |
| 10 | Real-Time Transform Gizmo | Three.js TransformControls / Inspector controls to edit X/Y/Z position & size | M3 | Survey |
| 11 | State Sync & Real-Time Persistence | Connect UI edit actions to backend PATCH API for real-time state persistence | M3 | Survey |
| 12 | E2E Opaque-Box Test Suite | Tier 1-4 requirement-driven E2E test suite and test runner | E2E | Survey |
| 13 | E2E Adversarial Coverage Hardening | Tier 5 white-box coverage hardening and edge-case testing | E2E | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Backend API & Data Persistence | FastAPI app, SQLite DB, SQLAlchemy models, Pydantic schemas, Project CRUD, 3D Model JSON endpoint, Element PATCH endpoint, unit tests | None | DONE |
| M2 | Frontend 3D Viewer & Layer Toggle UI | React + Vite app, Three.js canvas, OrbitControls, 3D layer grouping (Structural, Electrical, Plumbing), Layer Toggle UI panel | M1 | PLANNED |
| M3 | Real-Time Interactive Editing & State Sync | Raycast element selection, visual highlights, TransformControls gizmo, Property Inspector sidebar, live state sync via PATCH API | M2 | PLANNED |
| E2E | E2E Testing Track | Independent E2E test suite (Tiers 1-4) and Tier 5 adversarial hardening | M1, M2, M3 | PLANNED |

## Interface Contracts
### Backend API Contracts
- `POST /api/projects`: Creates a project and auto-generates 3D building layout JSON. Returns `201 Created`.
- `GET /api/projects`: Lists all projects. Returns `200 OK`.
- `GET /api/projects/{id}/model`: Fetches structured 3D building model (layers: `structural`, `electrical`, `plumbing`). Returns `200 OK`.
- `PATCH /api/projects/{id}/elements/{element_id}`: Updates element transform (`position`, `rotation`, `dimensions`). Returns `200 OK`.

### Frontend ↔ Three.js Scene Contracts
- Layer Groups: `structuralGroup`, `electricalGroup`, `plumbingGroup`.
- Toggle Rule: Setting `group.visible = true/false` dynamically updates canvas without reloading scene.
- Raycast Rule: Hidden layer groups are excluded from Raycaster hit testing.
