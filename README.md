# Builder 3D — Generative AI BIM & Architectural Engineering Platform

**Builder 3D** is an autonomous AI-driven Architectural BIM platform that generates, renders, and modifies structural OpenBIM models (LOD 100 to LOD 500) directly from conversational design briefs in real-time.

---

## 🏛️ Key Features

- **Principal AI Architect Meta-Agent**: Conversational discovery and real-time in-place architectural mutations with active-model state awareness.
- **Dynamic OpenBIM 3D Canvas**: Real-time WebGL/Three.js rendering engine with photorealistic PBR materials (Calacatta marble, fluted oak timber, low-E glass, fine woven fabrics, brushed metals).
- **Procedural Interior Suite Zoning**: Mathematically aligned, architecturally sound 2BHK and 3BHK residential floorplans with living lounges, open chef kitchens, master suites with acoustic headboards, spa bathrooms, and private balconies.
- **Level of Detail (LOD) Hierarchy**: Seamless transitions between:
  - **LOD 100**: Urban City Massing
  - **LOD 200**: Society & Campus Masterplan
  - **LOD 300**: Structural OpenBIM Envelope
  - **LOD 350**: Storey Partitioning & Floor Isolation
  - **LOD 400**: Furnished 2BHK / 3BHK Unit Interiors
  - **LOD 500**: MEP Engineering (415V Conduits & DN110 Drainage Stacks)
- **First-Person Walkthrough & Drone Tour**: Smooth WASD keyboard movement, pointer-lock camera orbit, and automated orbital drone tours.
- **Industry Standards Export**: Direct export to ISO 10303-21 IFC4, OBJ, and CAD JSON format.

---

## 🏗️ Architecture & Technology Stack

- **Frontend**: React 18, TypeScript, Three.js, Lucide React, Tailwind CSS / Vanilla CSS tokens, Vite
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic v2, Uvicorn
- **AI & BIM Engine**: Google Gemini API, IfcOpenShell (optional / extensible), Procedural Meta-Architect Agent

---

## 🚀 Getting Started

### 1. Backend Setup (FastAPI)
```bash
cd teamwork_projects/builder_ai/backend
python -m venv .venv
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup (React + Vite)
```bash
cd teamwork_projects/builder_ai/frontend_react
npm install
npm run dev
```

The application will be accessible at `http://localhost:5173`.

---

## 📄 License
MIT License
