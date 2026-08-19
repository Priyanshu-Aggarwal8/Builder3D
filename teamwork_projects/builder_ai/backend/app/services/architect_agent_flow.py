import json
import re
import uuid
from typing import Dict, Any, List, Optional
from app.services.meta_agent import meta_architect_agent

class ArchitectDiscoveryState:
    """
    Tracks conversational architectural state and design parameters for a project session.
    """
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.brief: Dict[str, Any] = {
            "project_name": "OpenBIM Architectural Project",
            "plot_dimensions": "40m x 60m (2,400 m²)",
            "floors": 12,
            "typology": "Commercial Office / Residential Complex",
            "unit_mix": "Custom Spatial Program",
            "facade_style": "High-Performance Double-Glazed Low-E Glass with Aluminum Mullions",
            "interior_style": "Contemporary Modern",
            "rooftop_amenity": "HVAC Chiller Plant & Solar PV Array",
            "mep_system": "3-Phase 415V Busbar & DN150 Vertical Wet Stacks",
        }
        self.conversation_history: List[Dict[str, str]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "brief": self.brief,
        }

# In-memory session store
DISCOVERY_SESSIONS: Dict[str, ArchitectDiscoveryState] = {}

class ArchitectConversationAgent:
    """
    Autonomous Principal AI Architect:
    - Synthesizes 3D OpenBIM building models directly from freeform natural language prompts on turn 1.
    - In-place surgical model mutations when user requests changes to active models.
    - Expert architectural consultation, spatial planning advice, and MEP guidance.
    - No rigid questionnaires or hardcoded 5-step blocking forms.
    """

    def get_or_create_session(self, session_id: Optional[str] = None) -> ArchitectDiscoveryState:
        if not session_id or session_id not in DISCOVERY_SESSIONS:
            new_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
            DISCOVERY_SESSIONS[new_id] = ArchitectDiscoveryState(new_id)
            return DISCOVERY_SESSIONS[new_id]
        return DISCOVERY_SESSIONS[session_id]

    def _is_creation_intent(self, prompt: str) -> bool:
        p = prompt.lower()
        create_keywords = [
            "design", "build", "create", "generate", "synthesize", "make a", "construct",
            "tower", "building", "story", "storey", "floor", "villa", "apartment",
            "commercial", "office", "headquarters", "hospital", "hotel", "penthouse",
            "mansion", "bungalow", "from scratch", "new project"
        ]
        return any(k in p for k in create_keywords) or len(p) > 25

    def _is_modification_intent(self, prompt: str) -> bool:
        p = prompt.lower()
        mod_keywords = [
            "change", "modify", "update", "replace", "add", "remove", "upgrade",
            "swap", "convert", "make the", "turn into", "reconfigure", "adjust",
            "facade", "mullion", "marble", "color", "material", "solar", "pool",
            "chiller", "balcony", "roof", "floors", "level"
        ]
        return any(k in p for k in mod_keywords)

    def process_turn(
        self,
        session_id: str,
        user_message: str,
        current_model: Optional[Dict[str, Any]] = None,
        synthesize_now: bool = False
    ) -> Dict[str, Any]:
        state = self.get_or_create_session(session_id)
        state.conversation_history.append({"role": "user", "content": user_message})

        msg_clean = user_message.strip()
        msg_lower = msg_clean.lower()

        # =========================================================================
        # CASE 1: In-Place Modification of Active Model (All Subsequent Commands)
        # =========================================================================
        is_new_creation = any(k in msg_lower for k in ["new building", "create new", "from scratch", "start over", "brand new project", "reset model"])
        
        if current_model and not is_new_creation and not synthesize_now:
            model_name = current_model.get("name", "Active Building")
            meta = current_model.get("meta", {})
            floors = meta.get("floors", 12)
            style = meta.get("style", "Contemporary Modern")

            updated_model = meta_architect_agent.modify_existing_model(current_model, user_message)
            all_elements_count = sum(len(l.get("elements", [])) for l in updated_model.get("layers", {}).values())

            ai_text = (
                f"✓ **Refined {updated_model.get('name', model_name)} in-place**:\n\n"
                f"• **Instruction Applied**: *\"{user_message}\"*\n"
                f"• **Active Scale**: {updated_model.get('meta', {}).get('floors', floors)} Stories • {updated_model.get('meta', {}).get('style', style)}\n"
                f"• **BIM Components**: {all_elements_count} elements active in viewport\n\n"
                f"The 3D model in your studio canvas has been updated in real-time."
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
                },
                "options": [],
                "quick_actions": [
                    "Upgrade to Luxury Calacatta Marble",
                    "Add Rooftop Chiller & Solar Array",
                    "Isolate Level 1 Storey",
                    "Export ISO 10303-21 IFC4"
                ]
            }

        # =========================================================================
        # CASE 2: Freeform Building Synthesis (Turn 1 Direct Creation)
        # =========================================================================
        if self._is_creation_intent(msg_lower) or synthesize_now or not current_model:
            # Directly synthesize model using the full architectural meta-agent
            new_model = meta_architect_agent.synthesize_model(user_message, project_id=1)
            
            meta = new_model.get("meta", {})
            floors = meta.get("floors", 12)
            style = meta.get("style", "Contemporary Modern")
            is_commercial = meta.get("typology") == "commercial" or "office" in msg_lower or "commercial" in msg_lower
            
            all_elements_count = sum(len(l.get("elements", [])) for l in new_model.get("layers", {}).values())

            # Format comprehensive architectural breakdown
            typology_label = "Grade-A Commercial Office Tower" if is_commercial else f"{floors}-Story Residential Complex"
            
            spatial_program = (
                "• **Ground & Entrance**: Double-height grand reception lobby with fluted timber wall & granite plaza\n"
                "• **Typical Office Floorplates**: Open-plan collaborative workstation clusters with ergonomic mesh task chairs\n"
                "• **Executive Suite**: 14-person Executive Boardroom with acoustic glass partitions & 85\" 4K media wall\n"
                "• **Focus & Breakout**: 3x Private Acoustic Phone Pods & Breakout Cafe/Pantry with waterfall island\n"
                "• **Restroom Battery**: Centralized male, female, and accessible wall-hung sensor WCs abutting the core"
            ) if is_commercial else (
                "• **Unit 1 (West Wing)**: Luxury 2BHK residence with open living suite, island kitchen, master bedroom, and sunset balcony\n"
                "• **Unit 2 (East Wing)**: Premium 3BHK residence with dining suite, master spa bath with soaking tub, and sunrise balcony\n"
                "• **Vertical Core**: High-speed dual elevator shafts and pressurized fire-escape stairwells"
            )

            mep_summary = (
                "• **Electrical**: 415V 3-phase main switchgear with vertical busbar riser & floor sub-panels\n"
                "• **Plumbing**: Coaxial vertical DN150 soil/waste wet stacks & DN100 vent stack with roof termination\n"
                "• **HVAC**: Central rooftop chiller plant distributing to floor VAV terminal units\n"
                "• **Lighting**: Architectural recessed 4000K LED troffer grid with daylight harvesting"
            )

            ai_text = (
                f"✨ **Architectural 3D Model Synthesized Successfully!**\n\n"
                f"### 🏢 Building Overview\n"
                f"• **Project**: **{new_model.get('name', 'Synthesized Building')}**\n"
                f"• **Typology**: {typology_label} ({floors} Levels • {floors * (3.8 if is_commercial else 3.2):.1f}m Height)\n"
                f"• **Aesthetic & Facade**: {style} with high-performance double-glazed curtain walls & aluminum mullions\n"
                f"• **Total BIM Entities**: **{all_elements_count} components** generated in real-time\n\n"
                f"### 📐 Spatial & Floorplate Program\n"
                f"{spatial_program}\n\n"
                f"### ⚡ Connected MEP Infrastructure\n"
                f"{mep_summary}\n\n"
                f"The 3D model is now live in your viewport. You can inspect individual storeys, enter first-person walkthrough mode, or request in-place modifications."
            )

            state.conversation_history.append({"role": "assistant", "content": ai_text})

            state.brief.update({
                "project_name": new_model.get("name", "Synthesized Building"),
                "floors": floors,
                "typology": typology_label,
                "interior_style": style,
                "mep_system": "3-Phase 415V Busbar & DN150 Vertical Wet Stacks",
            })

            quick_actions = [
                "Isolate Typical Floor",
                "Walk Inside First-Person",
                "Upgrade to Calacatta Marble",
                "Inspect Plumbing Risers",
                "Export ISO 10303-21 IFC4"
            ] if not is_commercial else [
                "Isolate Office Floor",
                "Inspect Boardroom & Workstations",
                "Check 415V Busduct & Wet Stacks",
                "Export ISO 10303-21 IFC4"
            ]

            return {
                "session_id": state.session_id,
                "message": ai_text,
                "model": new_model,
                "brief": state.brief,
                "options": [],
                "quick_actions": quick_actions
            }

        # =========================================================================
        # CASE 3: Architectural Consultation / Q&A
        # =========================================================================
        ai_text = (
            f"As your Principal AI Architect, here are recommendations for **{state.brief.get('project_name', 'your project')}**:\n\n"
            f"• **Structural Spans**: Recommended 8.0m × 8.0m post-tensioned column grid for optimal column-free lease spans.\n"
            f"• **Service Core**: Centralized reinforced concrete core hosting dual high-speed elevators, pressurized fire stairs, and vertical MEP chases.\n"
            f"• **MEP Riser Strategy**: Maintain strict coaxial vertical shaft alignment across all {state.brief.get('floors', 12)} storeys with zero axial drift (|ΔX|=0, |ΔZ|=0).\n\n"
            f"Would you like me to synthesize a 3D model with these exact parameters, or modify specific layers of the active model?"
        )

        state.conversation_history.append({"role": "assistant", "content": ai_text})

        return {
            "session_id": state.session_id,
            "message": ai_text,
            "brief": state.brief,
            "options": [],
            "quick_actions": [
                f"Synthesize {state.brief.get('floors', 12)}-Story Model Now",
                "Upgrade to Low-E Double Glazing",
                "Inspect Plumbing Wet Stacks",
                "Export ISO 10303-21 IFC4"
            ]
        }

architect_conversation_agent = ArchitectConversationAgent()
