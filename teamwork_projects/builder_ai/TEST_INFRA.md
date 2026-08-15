# E2E Test Infra: Builder AI Phase 1

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation design.
- Methodology: Category-Partition + BVA + Pairwise + Workload Testing.

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|---------------------|:------:|:------:|:------:|:------:|
| 1 | Full-Stack REST Backend API | R1 & AC 1 | 5 | 5 | ✓ | ✓ |
| 2 | Frontend 3D WebGL Canvas | R1 & AC 2 | 5 | 5 | ✓ | ✓ |
| 3 | Layer Toggle Controls | R2 & AC 3 | 5 | 5 | ✓ | ✓ |
| 4 | Real-Time Interactive Editing | R3 & AC 4 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test runner: Python `pytest` + `httpx` for Backend API, Playwright / Chrome DevTools runner for Frontend 3D Canvas rendering & UI interactions.
- Test case format: Automated test functions verifying HTTP status, JSON schema, console error absence, WebGL mesh visibility, and real-time state persistence.
- Directory layout: `tests_e2e/`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Create new project, verify backend API response and 3D model generation | F1, F2 | Medium |
| 2 | Load 3D model in WebGL canvas, toggle Structural/Electrical/Plumbing layers independently, verify 0 console errors | F2, F3 | High |
| 3 | Click 3D conduit in Electrical layer, move position via TransformControls, verify live UI update and backend state sync | F3, F4 | High |

## Coverage Thresholds
- Tier 1: ≥5 per feature
- Tier 2: ≥5 per feature (where boundaries exist)
- Tier 3: pairwise coverage of major feature interactions
- Tier 4: ≥5 realistic application scenarios
- Tier 5: Adversarial coverage hardening (white-box)
