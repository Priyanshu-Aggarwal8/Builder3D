import json
import re
import uuid
from typing import Dict, Any, List, Optional
from app.services.meta_agent import meta_architect_agent

class ArchitectDiscoveryState:
    """
    Tracks multi-turn architectural interview state machine for a project session.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.step_index = 0
        self.brief: Dict[str, Any] = {
            "project_name": "6-Story Residential Building",
            "plot_dimensions": "40m x 60m (2,400 m²)",
            "floors": 6,
            "typology": "Residential Complex",
            "unit_mix": "2 Units per floor (1x 2BHK West + 1x 3BHK East)",
            "facade_style": "Double-Glazed Low-E Glass with Black Aluminum Mullions",
            "interior_style": "Japandi Scandinavian",
            "balcony_style": "Cantilevered Teak Decks with Tempered Glass Balustrades",
            "rooftop_amenity": "Panoramic Sky Lounge & 18kWp Solar Array",
            "mep_system": "3-Phase 415V Busbar & DN110 PVC-U Soil Stacks",
            "has_city": False,
            "has_society": False,
        }
        self.conversation_history: List[Dict[str, str]] = []
        self.is_completed = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "step_index": self.step_index,
            "brief": self.brief,
            "is_completed": self.is_completed
        }

# In-memory session store
DISCOVERY_SESSIONS: Dict[str, ArchitectDiscoveryState] = {}

class ArchitectConversationAgent:
    """
    Stateful conversational agent conducting either:
    1. Active Model Consultation & In-Place Refinement (when a model is currently loaded in studio).
    2. Multi-step Architectural Discovery Interview (when starting a new project from scratch).
    """

    STEPS = [
        {
            "id": "site_and_plot",
            "question": "Step 1 of 5: What are the target plot dimensions and site area for this development?",
            "context": "Establishes setback requirements, ground coverage ratio, and structural foundation boundaries.",
            "options": [
                {"label": "40m × 60m Standard Plot (2,400 m²)", "value": "40m x 60m standard urban parcel with 2,400 m² plot area"},
                {"label": "50m × 80m High-Rise Parcel (4,000 m²)", "value": "50m x 80m high-density development parcel with 4,000 m² plot area"},
                {"label": "30m × 40m Boutique Parcel (1,200 m²)", "value": "30m x 40m boutique urban plot with 1,200 m² area"},
                {"label": "60m × 90m Masterplan Estate (5,400 m²)", "value": "60m x 90m masterplan estate parcel with 5,400 m² area"}
            ]
        },
        {
            "id": "building_height",
            "question": "Step 2 of 5: What is the desired building height and floor count?",
            "context": "Defines structural column dimensions, elevator core capacity, and vertical zoning FAR envelope.",
            "options": [
                {"label": "6 Stories (19.2m Height • Mid-Rise)", "value": "6-story mid-rise residential building with central core"},
                {"label": "12 Stories (38.4m Height • High-Rise)", "value": "12-story high-rise building with 3.2m floor-to-floor height"},
                {"label": "20 Stories (64.0m Height • Skyscraper)", "value": "20-story luxury high-rise tower with high-speed elevator shafts"},
                {"label": "2 Stories (6.4m Height • Luxury Villa)", "value": "2-story luxury minimalist cantilever villa with open living pavilion"}
            ]
        },
        {
            "id": "unit_mix",
            "question": "Step 3 of 5: How should each floor plate be programmed (Unit Mix & Layout)?",
            "context": "Organizes corridor circulation, entrance doors, living suites, kitchens, bedrooms, and bathrooms.",
            "options": [
                {"label": "Dual Units: 1x 2BHK West (110m²) + 1x 3BHK East (160m²)", "value": "2 units per floor: one 2BHK unit and one 3BHK unit with private balconies"},
                {"label": "Quad 2BHK Units (90m² each)", "value": "4 units per floor: four symmetrical 2BHK residences with corner balconies"},
                {"label": "Full-Floor Executive Penthouse Suite (380m²)", "value": "1 grand luxury 4BHK penthouse suite per floor with private elevator foyer"},
                {"label": "Commercial Open-Plan Corporate Floor", "value": "Open plan corporate office floor plate with central service core"}
            ]
        },
        {
            "id": "facade_and_aesthetic",
            "question": "Step 4 of 5: What architectural facade and interior aesthetic do you envision?",
            "context": "Applies materials, low-E glazing ratios, mullion framing, and interior finish harmonizations.",
            "options": [
                {"label": "Japandi Scandinavian (Light Oak + Black Mullions)", "value": "Japandi Scandinavian aesthetic with light oak timbers, fluted walls, and black aluminum curtain facade"},
                {"label": "Luxury Calacatta (Italian Marble + Bronze)", "value": "Luxury Calacatta marble, brushed bronze trims, and floor-to-ceiling tinted curtain glass"},
                {"label": "Industrial Loft (Architectural Concrete + Steel)", "value": "Industrial Loft with architectural concrete, exposed steel mullions, and smoked glass"},
                {"label": "Biophilic Green (Staggered Terraces + Teak)", "value": "Biophilic architecture with vertical planter terraces, natural teak decks, and solar pergolas"}
            ]
        },
        {
            "id": "rooftop_and_mep",
            "question": "Step 5 of 5: What rooftop amenities and engineering MEP specifications are required?",
            "context": "Finalizes elevator machine overrun, solar PV array capacity, and vertical utility shafts.",
            "options": [
                {"label": "Panoramic Sky Lounge + 18kWp Solar Array", "value": "Rooftop panoramic sky terrace with timber pergola, mechanical screening, and 18kWp solar array"},
                {"label": "Infinity Edge Rooftop Swimming Pool & Deck", "value": "Rooftop infinity swimming pool with lounge deck and glass windbreak balustrades"},
                {"label": "High-Efficiency VRF Chiller Plant + Solar", "value": "Rooftop VRF chiller plant, solar PV array, and 415V electrical distribution"},
                {"label": "Standard Mechanical Overrun Penthouse", "value": "Enclosed elevator machine room penthouse with standard drainage stacks"}
            ]
        }
    ]

    def get_or_create_session(self, session_id: Optional[str] = None) -> ArchitectDiscoveryState:
        if not session_id or session_id not in DISCOVERY_SESSIONS:
            new_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
            DISCOVERY_SESSIONS[new_id] = ArchitectDiscoveryState(new_id)
            return DISCOVERY_SESSIONS[new_id]
        return DISCOVERY_SESSIONS[session_id]

    def process_turn(
        self,
        session_id: str,
        user_message: str,
        current_model: Optional[Dict[str, Any]] = None,
        synthesize_now: bool = False
    ) -> Dict[str, Any]:
        state = self.get_or_create_session(session_id)
        state.conversation_history.append({"role": "user", "content": user_message})

        msg_lower = user_message.lower()

        # =========================================================================
        # CASE A: Active Model In-Place Customization
        # =========================================================================
        if current_model and not ("create new" in msg_lower or "from scratch" in msg_lower or "start over" in msg_lower):
            model_name = current_model.get("name", "Active Building")
            meta = current_model.get("meta", {})
            floors = meta.get("floors", 6)
            style = meta.get("style", "Contemporary")

            # Mutate model in place
            updated_model = meta_architect_agent.modify_existing_model(current_model, user_message)
            all_elements_count = sum(len(l.get("elements", [])) for l in updated_model.get("layers", {}).values())

            ai_text = (
                f"✓ **Refined {updated_model.get('name', model_name)} in-place** based on your instruction:\n\n"
                f"• **Customization**: *\"{user_message}\"*\n"
                f"• **Active Building Scale**: {updated_model.get('meta', {}).get('floors', floors)} Stories • {updated_model.get('meta', {}).get('style', style)}\n"
                f"• **BIM Elements**: {all_elements_count} entities updated\n\n"
                f"The 3D model in your studio has been updated in real-time. Would you like to further refine room boundaries, add luxury finishes, or reconfigure MEP layers?"
            )

            state.conversation_history.append({"role": "assistant", "content": ai_text})

            return {
                "session_id": state.session_id,
                "message": ai_text,
                "model": updated_model,
                "brief": {
                    "project_name": updated_model.get("name", model_name),
                    "floors": updated_model.get("meta", {}).get("floors", floors),
                    "interior_style": updated_model.get("meta", {}).get("style", style),
                    "unit_mix": "2 Units per floor (1x 2BHK West + 1x 3BHK East)",
                    "rooftop_amenity": "Sky Lounge & Solar Pergola",
                },
                "is_ready_for_synthesis": False,
                "options": [
                    {"label": "Upgrade to Calacatta Marble Finishes", "value": "Upgrade all countertops and flooring to luxury Calacatta marble"},
                    {"label": "Add Rooftop Infinity Pool & Lounge", "value": "Add infinity swimming pool and sunset lounge to the rooftop"},
                    {"label": "Convert Level 3 to Penthouse Suite", "value": "Reconfigure Level 3 into a grand full-floor penthouse suite"},
                    {"label": "Add Balcony Greenery & Planters", "value": "Add biophilic vertical planter boxes and teak deck louvers to all balconies"}
                ],
                "quick_actions": [
                    "Upgrade to Calacatta Marble",
                    "Add Rooftop Pool",
                    "Add Balcony Planters",
                    "Export ISO 10303-21 IFC4"
                ]
            }

        # =========================================================================
        # CASE B: Discovery Flow (New Project From Scratch)
        # =========================================================================
        current_step_idx = state.step_index

        if current_step_idx < len(self.STEPS) and not synthesize_now:
            step_data = self.STEPS[current_step_idx]
            state.step_index += 1
            is_final_step = (state.step_index >= len(self.STEPS))

            ai_text = (
                f"Recorded specifications for **{state.brief['project_name']}**.\n\n"
                f"**{step_data['question']}**\n\n"
                f"*{step_data['context']}*"
            )

            state.conversation_history.append({"role": "assistant", "content": ai_text})

            return {
                "session_id": state.session_id,
                "message": ai_text,
                "step_index": state.step_index,
                "total_steps": len(self.STEPS),
                "current_step": step_data,
                "brief": state.brief,
                "is_ready_for_synthesis": is_final_step,
                "options": step_data["options"],
                "quick_actions": [
                    "Synthesize 3D Model Now",
                    "6 Stories (2BHK + 3BHK)",
                    "Japandi Style",
                    "Add Rooftop Pool"
                ]
            }
        else:
            state.is_completed = True
            compiled_prompt = (
                f"{state.brief['floors']}-story building with {state.brief['unit_mix']}, "
                f"{state.brief['interior_style']} style, {state.brief['facade_style']}, "
                f"{state.brief['rooftop_amenity']}"
            )
            new_model = meta_architect_agent.synthesize_model(compiled_prompt, 1)

            ai_text = (
                f"✨ **Architectural Model Synthesized!**\n\n"
                f"• **Project**: {state.brief['project_name']} ({state.brief['floors']} Stories)\n"
                f"• **Unit Program**: {state.brief['unit_mix']}\n"
                f"• **Aesthetic**: {state.brief['interior_style']} with {state.brief['facade_style']}\n"
                f"• **Rooftop & MEP**: {state.brief['rooftop_amenity']} | {state.brief['mep_system']}\n\n"
                f"Synthesized full OpenBIM 3D model with structural columns, elevator cores, realistic room partitions, and MEP systems."
            )
            state.conversation_history.append({"role": "assistant", "content": ai_text})

            return {
                "session_id": state.session_id,
                "message": ai_text,
                "model": new_model,
                "step_index": len(self.STEPS),
                "total_steps": len(self.STEPS),
                "current_step": None,
                "brief": state.brief,
                "is_ready_for_synthesis": True,
                "options": [],
                "quick_actions": [
                    "Isolate Level 1 Storey",
                    "Walk Inside 2BHK Unit",
                    "Upgrade to Calacatta Marble",
                    "Export ISO 10303-21 IFC4"
                ]
            }

architect_conversation_agent = ArchitectConversationAgent()
