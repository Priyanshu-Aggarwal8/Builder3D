# Original User Request

## 2026-08-09T16:18:01Z

# Teamwork Project Prompt — Draft

Build a production-ready first phase of the Builder AI app based on the provided architecture docs. The core feature is a real-time editable 3D building model where structural, electrical, and plumbing layers can be visualized and modified interactively.

Working directory: c:/Users/SHIVA/Desktop/BuilderAI/teamwork_projects/builder_ai
Integrity mode: development

## Requirements

### R1. Full-Stack Application
Build a backend to serve and manage 3D model data, and a frontend web application to render the interactive UI. The agent team is free to choose the most efficient web frameworks (e.g. FastAPI/Angular, Node/React, Python/Vanilla JS) to achieve the real-time 3D editing goal quickly.

### R2. Interactive 3D Viewer with Layers
Implement a 3D canvas that displays a building model containing distinct, toggleable functional layers (e.g., structural, electrical wiring, water pipelines).

### R3. Real-Time Editing
Implement interactive controls allowing the user to modify the 3D model in real-time (e.g., moving an object, wall, or pipeline) and have the system update the state accordingly.

## Acceptance Criteria

### API & Rendering
- [ ] The backend API exposes an endpoint that successfully serves structured 3D model data (e.g., JSON, GLTF, or OBJ).
- [ ] The frontend successfully loads the 3D data and renders it in a 3D canvas (e.g., using Three.js) without browser console errors.

### Interaction
- [ ] The UI provides visible toggle controls to independently show or hide at least two distinct building layers (e.g., "Electrical", "Plumbing").
- [ ] The UI allows the user to interactively modify at least one element in the 3D space, and the visual change is reflected in real-time.
