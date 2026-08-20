import json
import re
import uuid
from typing import Dict, Any, List, Optional, Tuple
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
            "floors": 2,
            "typology": "Residential Villa / Multi-Storey Complex",
            "unit_mix": "Custom Spatial Program",
            "facade_style": "Contemporary Modern with Double Glazing & Aluminum Mullions",
            "interior_style": "Contemporary Modern",
            "rooftop_amenity": "Rooftop Terrace & HVAC Service Enclosure",
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
    - Expert architectural consultation, spatial planning advice, and MEP guidance without hallucinating model changes.
    - Strict context isolation preventing accidental floor count resets or unwanted typology conversions.
    """

    def get_or_create_session(self, session_id: Optional[str] = None) -> ArchitectDiscoveryState:
        if not session_id or session_id not in DISCOVERY_SESSIONS:
            new_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
            DISCOVERY_SESSIONS[new_id] = ArchitectDiscoveryState(new_id)
            return DISCOVERY_SESSIONS[new_id]
        return DISCOVERY_SESSIONS[session_id]

    def _extract_active_model_meta(self, model: Dict[str, Any]) -> Tuple[int, str, str]:
        """
        Reliably extracts actual floor count, typology, and architectural style from the active model geometry.
        """
        meta = model.get("meta", {})
        name_l = model.get("name", "").lower()

        # 1. Floor count extraction
        floors = meta.get("floors")
        if not floors:
            # Check model name for floor count e.g. "3-storey", "3 story", "12-story"
            m_name_floor = re.search(r'(\d+)\s*(?:-|\s)*(?:story|storey|floor|stories|floors|level|levels)', name_l)
            if m_name_floor:
                floors = int(m_name_floor.group(1))
            else:
                # Scan element elevations
                all_els = []
                for layer in model.get("layers", {}).values():
                    all_els.extend(layer.get("elements", []))
                all_els.extend(model.get("generated_elements", []))
                elevations = [el.get("position", [0, 0, 0])[1] for el in all_els if el.get("type") in ["slab", "wall"]]
                max_y = max(elevations, default=3.2)
                floors = max(1, round(max_y / 3.2))

        # 2. Typology extraction
        typology = meta.get("typology")
        if not typology:
            if any(k in name_l for k in ["commercial", "office", "headquarters", "tower"]):
                typology = "commercial"
            elif any(k in name_l for k in ["villa", "mansion", "house", "residence", "bungalow"]):
                typology = "villa"
            elif any(k in name_l for k in ["penthouse", "apartment"]):
                typology = "apartment"
            else:
                typology = "residential"

        # 3. Style extraction
        style = meta.get("style")
        if not style:
            if "japandi" in name_l:
                style = "Japandi Scandinavian"
            elif "biophilic" in name_l:
                style = "Biophilic Green"
            elif typology == "commercial":
                style = "Corporate Modern"
            else:
                style = "Contemporary Modern"

        return floors, typology, style

    def _is_question_or_inquiry(self, prompt: str) -> bool:
        """
        Identifies whether a message is an architectural question or inquiry rather than a 3D geometry modification command.
        """
        p = prompt.strip().lower()
        if p.endswith("?"):
            return True

        question_triggers = [
            "why", "how", "what", "where", "which", "who", "when",
            "can you explain", "explain why", "explain how", "explain the",
            "tell me about", "tell me why", "is there", "does the", "why is",
            "why does", "why are", "why would", "is it possible", "can we have",
            "what is", "how many", "does it have", "why do"
        ]

        # Explicit modification verbs override question words if present as a direct command
        change_commands = [
            "change the", "make the", "replace the", "add a", "add the", "remove the",
            "delete the", "switch to", "convert to", "set the", "turn the"
        ]
        if any(cmd in p for cmd in change_commands):
            return False

        return any(p.startswith(q) or f" {q} " in f" {p} " for q in question_triggers)

    def _is_creation_intent(self, prompt: str) -> bool:
        p = prompt.lower()
        create_keywords = [
            "design a new", "build a new", "create a new", "generate a new", "synthesize a new",
            "from scratch", "brand new project", "reset and build", "start over"
        ]
        return any(k in p for k in create_keywords)

    def _handle_architectural_inquiry(
        self,
        question: str,
        current_model: Dict[str, Any],
        floors: int,
        typology: str,
        style: str
    ) -> str:
        """
        Generates domain-grounded architectural explanations without altering the 3D model.
        """
        q = question.lower()
        model_name = current_model.get("name", "Active Building")

        # 1. Elevator / Lift reaching roof inquiry
        if any(k in q for k in ["lift", "elevator", "hoist", "shaft"]) and any(k in q for k in ["roof", "top", "reach", "extend", "overrun", "high"]):
            return (
                f"### 🏗️ Architectural Core Design: Elevator Overrun & Rooftop Access\n\n"
                f"In the active **{floors}-storey {typology}** model (*{model_name}*), the elevator core extends above the upper roof slab for two standard architectural & engineering reasons:\n\n"
                f"1. **Traction Hoistway Overrun & Safety Clearances**:\n"
                f"   • Building codes (EN 81-20 / ASME A17.1) mandate a vertical headroom overrun of **1.2m to 2.4m** above the top passenger landing. This accommodates the traction hoist sheaves, governor machinery, and top-of-car refuge safety space.\n\n"
                f"2. **Rooftop Terrace & Mechanical Egress**:\n"
                f"   • When a building features an accessible rooftop terrace, solar PV array, or HVAC plant, the core terminates in a weather-tight rooftop vestibule/lobby for occupant egress and service maintenance.\n\n"
                f"💡 *Would you like me to cap the lift core flush below the roof, or design an enclosed rooftop sky lounge around it?*"
            )

        # 2. Columns & Structural Grid inquiry
        if any(k in q for k in ["column", "pillar", "structural", "load", "beam", "shear", "grid"]):
            return (
                f"### 🏛️ Structural Engineering Grid ({floors} Storeys)\n\n"
                f"• **Column Matrix**: Configured on a **6.0m × 8.0m bay spacing** with reinforced concrete (RC) square columns.\n"
                f"• **Lateral Stability**: A central reinforced concrete shear core resists wind loads and seismic shear.\n"
                f"• **Floor System**: 300mm post-tensioned flat slabs provide column-free interior flexibility with minimal deflection."
            )

        # 3. MEP (Plumbing, Electrical, HVAC) inquiry
        if any(k in q for k in ["plumb", "water", "pipe", "drain", "stack", "sewer", "elec", "power", "hvac", "chiller"]):
            return (
                f"### ⚡ Connected MEP Infrastructure Breakdown\n\n"
                f"• **Plumbing**: Vertical DN150 cast-iron soil/waste stacks run continuously from Ground to Roof with rooftop atmospheric vent terminations.\n"
                f"• **Electrical**: 415V 3-phase busbar risers distribute to dedicated floor sub-distribution boards.\n"
                f"• **HVAC**: Rooftop chiller/condenser units connect to concealed ceiling fan coil units with fresh air heat recovery."
            )

        # 4. Setbacks & Zoning inquiry
        if any(k in q for k in ["setback", "zoning", "far", "boundary", "height cap", "coverage"]):
            return (
                f"### 📐 Site Zoning & Setback Envelope\n\n"
                f"• **Front Setback**: 4.0m landscaped frontage buffer.\n"
                f"• **Rear & Side Setbacks**: 3.0m fire separation clear distances.\n"
                f"• **Max Height**: Designed at {floors * 3.4:.1f}m within local zoning height caps."
            )

        # 5. General Architectural consultation fallback
        return (
            f"### 🏛️ Principal Architectural Consultation\n\n"
            f"Regarding *\"{question}\"* on the active **{floors}-storey {typology}** (*{model_name}*):\n\n"
            f"• **Current Program**: {floors} storeys designed in {style} aesthetic with integrated BIM structural and MEP layers.\n"
            f"• **Architectural Intent**: Optimized for daylight harvesting, spatial circulation efficiency, and acoustic separation.\n\n"
            f"Would you like me to make specific design adjustments to the active 3D model?"
        )

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
        # CASE 1: Architectural Inquiry / Question (Model Left Intact, Zero Drift)
        # =========================================================================
        if current_model and self._is_question_or_inquiry(user_message):
            floors, typology, style = self._extract_active_model_meta(current_model)
            model_name = current_model.get("name", f"{floors}-Storey {typology.title()}")

            ai_text = self._handle_architectural_inquiry(
                question=user_message,
                current_model=current_model,
                floors=floors,
                typology=typology,
                style=style
            )

            state.conversation_history.append({"role": "assistant", "content": ai_text})

            return {
                "session_id": state.session_id,
                "message": ai_text,
                "is_inquiry": True,
                "model": current_model,  # Model preserved 100% unchanged!
                "brief": {
                    "project_name": model_name,
                    "floors": floors,
                    "typology": typology,
                    "interior_style": style,
                },
                "options": [],
                "quick_actions": [
                    "Cap Lift Flush Below Roof",
                    "Add Rooftop Terrace Pergola",
                    "Inspect Level 1 Storey",
                    "Export ISO 10303-21 IFC4"
                ]
            }

        # =========================================================================
        # CASE 2: In-Place Modification of Active Model (Commands & Mutations)
        # =========================================================================
        is_new_creation = self._is_creation_intent(msg_lower)

        if current_model and not is_new_creation and not synthesize_now:
            floors, typology, style = self._extract_active_model_meta(current_model)
            model_name = current_model.get("name", "Active Building")

            updated_model = meta_architect_agent.modify_existing_model(current_model, user_message)
            new_floors, new_typology, new_style = self._extract_active_model_meta(updated_model)
            all_elements_count = sum(len(l.get("elements", [])) for l in updated_model.get("layers", {}).values())

            ai_text = (
                f"✓ **Refined {updated_model.get('name', model_name)} in-place**:\n\n"
                f"• **Instruction Applied**: *\"{user_message}\"*\n"
                f"• **Active Scale**: {new_floors} Storeys • {new_style}\n"
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
                    "floors": new_floors,
                    "typology": new_typology,
                    "interior_style": new_style,
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
        # CASE 3: Freeform Building Synthesis (Turn 1 Direct Creation)
        # =========================================================================
        if is_new_creation or synthesize_now or not current_model:
            new_model = meta_architect_agent.synthesize_model(user_message, project_id=1)
            floors, typology, style = self._extract_active_model_meta(new_model)
            is_commercial = typology == "commercial"

            all_elements_count = sum(len(l.get("elements", [])) for l in new_model.get("layers", {}).values())
            typology_label = "Grade-A Commercial Office Tower" if is_commercial else f"{floors}-Story Residential Building"

            spatial_program = (
                "• **Ground & Entrance**: Double-height grand reception lobby with fluted timber wall & granite plaza\n"
                "• **Typical Office Floorplates**: Open-plan collaborative workstation clusters with ergonomic mesh task chairs\n"
                "• **Executive Suite**: 14-person Executive Boardroom with acoustic glass partitions & 85\" 4K media wall\n"
                "• **Focus & Breakout**: 3x Private Acoustic Phone Pods & Breakout Cafe/Pantry with waterfall island\n"
                "• **Restroom Battery**: Centralized male, female, and accessible wall-hung sensor WCs abutting the core"
            ) if is_commercial else (
                "• **Living Suite**: Open-plan great room with bouclé sectional sofa, marble coffee table, and panoramic glazing\n"
                "• **Kitchen & Dining**: Waterfall quartz kitchen island with undermount sink, induction hob, and 8-seat walnut dining set\n"
                "• **Master Suite**: King platform bed with 3.2m acoustic fluted headboard, walk-in closet, and private balcony deck\n"
                "• **Spa Bathrooms**: Freestanding soaking tub with chrome gooseneck mixer and double vanity"
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

        # Fallback consultation
        floors = state.brief.get("floors", 2)
        ai_text = (
            f"As your Principal AI Architect, here are recommendations for **{state.brief.get('project_name', 'your project')}**:\n\n"
            f"• **Structural Spans**: Recommended 8.0m × 8.0m column grid for open floorplate flexibility.\n"
            f"• **Service Core**: Centralized reinforced concrete core hosting elevators, fire stairs, and vertical MEP chases.\n"
            f"• **MEP Riser Strategy**: Coaxial vertical shaft alignment across all storeys with zero axial drift.\n\n"
            f"Would you like me to synthesize a 3D model with these exact parameters, or modify specific layers of the active model?"
        )

        state.conversation_history.append({"role": "assistant", "content": ai_text})

        return {
            "session_id": state.session_id,
            "message": ai_text,
            "brief": state.brief,
            "options": [],
            "quick_actions": [
                f"Synthesize {floors}-Story Model Now",
                "Upgrade to Low-E Double Glazing",
                "Inspect Plumbing Wet Stacks",
                "Export ISO 10303-21 IFC4"
            ]
        }

architect_conversation_agent = ArchitectConversationAgent()
