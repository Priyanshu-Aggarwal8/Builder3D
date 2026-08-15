import { BuildingModel, BuildingLayer, ModelElement } from '../types/model';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export const defaultVillaModel: BuildingModel = {
  id: 1,
  name: "Vinewood Luxury Villa (AAA ArchViz)",
  version: 1,
  description: "Full-scale AAA architectural mansion with rooftop HVAC chiller plant, multi-room furnished interior, infinity pool, and integrated MEP systems.",
  layers: {
    structural: {
      id: "structural",
      name: "Structural Layer",
      visible: true,
      color: "#D4FF32",
      elements: [
        // Site & Groundwork
        { id: "site_podium", name: "Site Grade Platform & Driveway", type: "slab", layerId: "structural", position: [0, -0.2, 2.0], dimensions: { width: 24, height: 0.35, depth: 23 }, material: { color: "#1E212B", opacity: 1.0, roughness: 0.9 } },
        { id: "entry_steps", name: "Architectural Concrete Entry Steps", type: "slab", layerId: "structural", position: [4.0, 0.05, 9.5], dimensions: { width: 3.6, height: 0.15, depth: 4.0 }, material: { color: "#334155", opacity: 1.0, roughness: 0.8 } },
        { id: "planter_w", name: "West Perimeter Concrete Planter", type: "wall", layerId: "structural", position: [-10.0, 0.4, 0], dimensions: { width: 1.2, height: 0.8, depth: 17.0 }, material: { color: "#1E293B", opacity: 1.0 } },
        { id: "hedge_w", name: "West Boxwood Green Hedge", type: "fixture", layerId: "structural", position: [-10.0, 1.0, 0], dimensions: { width: 0.9, height: 0.7, depth: 16.5 }, material: { color: "#15803D", opacity: 1.0, roughness: 0.95 } },
        
        // Level 1 Foundation & Flooring
        { id: "slab_l1", name: "Level 1 Main Slab (16x13m)", type: "slab", layerId: "structural", position: [0, -0.15, 0], dimensions: { width: 16.4, height: 0.3, depth: 13.4 }, material: { color: "#0F172A", opacity: 1.0, roughness: 0.75 } },
        { id: "floor_oak_l1", name: "Level 1 Oak Hardwood Flooring", type: "slab", layerId: "structural", position: [0, 0.01, 0], dimensions: { width: 16.0, height: 0.02, depth: 13.0 }, material: { color: "#C9935E", opacity: 1.0, roughness: 0.55 } },
        
        // Heavy RC Pillars
        { id: "col_sw", name: "Ground RC Pillar SW", type: "column", layerId: "structural", position: [-7.5, 1.8, 6.0], dimensions: { width: 0.45, height: 3.6, depth: 0.45 }, material: { color: "#475569", opacity: 1.0 } },
        { id: "col_se", name: "Ground RC Pillar SE", type: "column", layerId: "structural", position: [7.5, 1.8, 6.0], dimensions: { width: 0.45, height: 3.6, depth: 0.45 }, material: { color: "#475569", opacity: 1.0 } },
        { id: "col_nw", name: "Ground RC Pillar NW", type: "column", layerId: "structural", position: [-7.5, 1.8, -6.0], dimensions: { width: 0.45, height: 3.6, depth: 0.45 }, material: { color: "#475569", opacity: 1.0 } },
        { id: "col_ne", name: "Ground RC Pillar NE", type: "column", layerId: "structural", position: [7.5, 1.8, -6.0], dimensions: { width: 0.45, height: 3.6, depth: 0.45 }, material: { color: "#475569", opacity: 1.0 } },
        
        // Ground Walls
        { id: "wall_north_l1", name: "Level 1 North Facade Wall", type: "wall", layerId: "structural", position: [0, 1.8, -6.5], dimensions: { width: 16.0, height: 3.6, depth: 0.25 }, material: { color: "#E2E8F0", opacity: 1.0 } },
        { id: "wall_west_l1", name: "Level 1 West Shear Wall", type: "wall", layerId: "structural", position: [-8.0, 1.8, 0], dimensions: { width: 0.25, height: 3.6, depth: 13.0 }, material: { color: "#E2E8F0", opacity: 1.0 } },
        { id: "glass_facade_l1", name: "Great Room Glass Curtain Wall", type: "window", layerId: "structural", position: [-2.5, 1.8, 6.5], dimensions: { width: 10.5, height: 3.3, depth: 0.08 }, material: { color: "#38BDF8", opacity: 0.35, transmission: 0.92 } },
        
        // Living Room Furnishings
        { id: "media_wall", name: "Living Room Media Feature Wall", type: "wall", layerId: "structural", position: [-7.85, 1.6, 2.5], dimensions: { width: 0.3, height: 3.0, depth: 4.5 }, material: { color: "#0F172A", opacity: 1.0 } },
        { id: "fireplace_fire", name: "Linear Inset LED Fireplace", type: "fixture", layerId: "structural", position: [-7.75, 0.6, 2.5], dimensions: { width: 0.2, height: 0.35, depth: 2.2 }, material: { color: "#F59E0B", opacity: 1.0 } },
        { id: "sofa_main", name: "Low-Profile Boucle Sectional Sofa", type: "fixture", layerId: "structural", position: [-4.5, 0.45, 2.5], dimensions: { width: 3.4, height: 0.75, depth: 2.2 }, material: { color: "#334155", opacity: 1.0 } },
        { id: "coffee_table", name: "Calacatta Marble Coffee Table", type: "fixture", layerId: "structural", position: [-4.5, 0.22, 2.5], dimensions: { width: 1.6, height: 0.38, depth: 0.9 }, material: { color: "#F8FAFC", opacity: 1.0 } },
        
        // Kitchen & Dining
        { id: "kitchen_part", name: "Kitchen Architectural Partition", type: "wall", layerId: "structural", position: [-1.0, 1.8, -2.5], dimensions: { width: 0.2, height: 3.6, depth: 6.5 }, material: { color: "#334155", opacity: 1.0 } },
        { id: "kitchen_island", name: "Calacatta Gold Waterfall Kitchen Island", type: "fixture", layerId: "structural", position: [-4.5, 0.5, -2.5], dimensions: { width: 3.2, height: 0.95, depth: 1.2 }, material: { color: "#F8FAFC", opacity: 1.0 } },
        { id: "dining_table", name: "Solid Walnut 8-Seater Dining Table", type: "fixture", layerId: "structural", position: [3.5, 0.45, -2.5], dimensions: { width: 2.6, height: 0.75, depth: 1.1 }, material: { color: "#78350F", opacity: 1.0 } },
        { id: "stairs_flight", name: "Architectural Floating Timber Staircase", type: "slab", layerId: "structural", position: [5.5, 1.8, 1.5], dimensions: { width: 1.4, height: 3.6, depth: 3.2 }, material: { color: "#C9935E", opacity: 1.0 } },
        { id: "front_door", name: "Custom 2.8m Walnut Pivot Front Door", type: "door", layerId: "structural", position: [4.0, 1.4, 6.5], dimensions: { width: 1.6, height: 2.8, depth: 0.15 }, material: { color: "#B45309", opacity: 1.0 } },

        // Level 2
        { id: "slab_l2", name: "Level 2 Floor Slab (16x13m)", type: "slab", layerId: "structural", position: [0, 3.45, 0], dimensions: { width: 16.4, height: 0.3, depth: 13.4 }, material: { color: "#0F172A", opacity: 1.0, roughness: 0.75 } },
        { id: "wall_north_l2", name: "Level 2 North Facade Wall", type: "wall", layerId: "structural", position: [0, 5.4, -6.5], dimensions: { width: 16.0, height: 3.6, depth: 0.25 }, material: { color: "#E2E8F0", opacity: 1.0 } },
        { id: "master_bed", name: "Master Suite King Platform Bed", type: "fixture", layerId: "structural", position: [-4.5, 3.95, 1.5], dimensions: { width: 2.2, height: 0.6, depth: 2.4 }, material: { color: "#475569", opacity: 1.0 } },
        { id: "bed_headboard", name: "Fluted Acoustic Oak Master Headboard", type: "wall", layerId: "structural", position: [-4.5, 4.8, 2.75], dimensions: { width: 3.6, height: 1.8, depth: 0.15 }, material: { color: "#C9935E", opacity: 1.0 } },
        { id: "master_balcony_deck", name: "Cantilevered Master Balcony Deck", type: "slab", layerId: "structural", position: [-3.5, 3.5, 8.0], dimensions: { width: 9.0, height: 0.25, depth: 3.0 }, material: { color: "#334155", opacity: 1.0 } },
        { id: "balcony_glass_rail", name: "Balcony Tempered Glass Balustrade", type: "window", layerId: "structural", position: [-3.5, 4.15, 9.45], dimensions: { width: 9.0, height: 1.1, depth: 0.06 }, material: { color: "#38BDF8", opacity: 0.4, transmission: 0.95 } },

        // Rooftop Infrastructure
        { id: "roof_main_slab", name: "Overhanging Architectural Roof Slab", type: "slab", layerId: "structural", position: [0, 7.1, 0], dimensions: { width: 17.6, height: 0.35, depth: 14.6 }, material: { color: "#0F172A", opacity: 1.0 } },
        { id: "roof_parapet_n", name: "Rooftop Parapet Perimeter Coping North", type: "wall", layerId: "structural", position: [0, 7.7, -7.2], dimensions: { width: 17.6, height: 1.0, depth: 0.2 }, material: { color: "#334155", opacity: 1.0 } },
        { id: "roof_parapet_s", name: "Rooftop Parapet Perimeter Coping South", type: "wall", layerId: "structural", position: [0, 7.7, 7.2], dimensions: { width: 17.6, height: 1.0, depth: 0.2 }, material: { color: "#334155", opacity: 1.0 } },
        { id: "roof_penthouse_box", name: "Rooftop Elevator & Stair Penthouse", type: "wall", layerId: "structural", position: [4.5, 8.6, 0], dimensions: { width: 3.8, height: 2.8, depth: 4.2 }, material: { color: "#1E293B", opacity: 1.0 } },

        // Outdoor Infinity Pool & Fire Pit
        { id: "pool_water_volume", name: "Resort-Grade Infinity Pool Water", type: "slab", layerId: "structural", position: [-2.0, -0.15, 11.0], dimensions: { width: 8.5, height: 0.4, depth: 4.8 }, material: { color: "#06B6D4", opacity: 0.85, transmission: 0.8 } },
        { id: "pool_teak_deck", name: "Teak Wood Pool Sun Deck", type: "slab", layerId: "structural", position: [-2.0, 0.05, 11.0], dimensions: { width: 11.5, height: 0.12, depth: 6.8 }, material: { color: "#B45309", opacity: 1.0, roughness: 0.85 } },
        { id: "firepit_bench", name: "Sunken Fire Pit Concrete Lounge Bench", type: "slab", layerId: "structural", position: [4.5, -0.1, 11.0], dimensions: { width: 3.6, height: 0.45, depth: 3.6 }, material: { color: "#334155", opacity: 1.0 } },
        { id: "firepit_burner", name: "Natural Basalt Stone Fire Pit Burner", type: "fixture", layerId: "structural", position: [4.5, 0.15, 11.0], dimensions: { width: 1.2, height: 0.35, depth: 1.2 }, material: { color: "#F59E0B", opacity: 1.0 } },
      ],
    },
    electrical: {
      id: "electrical",
      name: "Electrical System",
      visible: true,
      color: "#F59E0B",
      elements: [
        { id: "elec_main_panel", name: "Main 200A Electrical Distribution Panel", type: "fixture", layerId: "electrical", position: [-7.8, 1.2, -5.3], dimensions: { width: 0.18, height: 1.1, depth: 0.75 }, material: { color: "#F59E0B", opacity: 1.0 } },
        { id: "elec_vertical_conduit", name: "Vertical 32mm High-Voltage Conduit Chase", type: "conduit", layerId: "electrical", position: [-7.7, 3.6, -5.3], dimensions: { width: 0.15, height: 7.2, depth: 0.15 }, material: { color: "#FBBF24", opacity: 1.0 } },
        { id: "hvac_chiller_1", name: "Commercial Rooftop HVAC Chiller Unit A", type: "fixture", layerId: "electrical", position: [-4.5, 7.9, -3.0], dimensions: { width: 2.2, height: 1.4, depth: 1.8 }, material: { color: "#475569", opacity: 1.0 } },
        { id: "hvac_chiller_2", name: "Commercial Rooftop HVAC Chiller Unit B", type: "fixture", layerId: "electrical", position: [-4.5, 7.9, 1.5], dimensions: { width: 2.2, height: 1.4, depth: 1.8 }, material: { color: "#475569", opacity: 1.0 } },
        { id: "solar_panel_array", name: "Photovoltaic Solar Panel Array", type: "slab", layerId: "electrical", position: [-1.0, 7.55, -2.5], dimensions: { width: 4.5, height: 0.15, depth: 3.5 }, material: { color: "#1E3A8A", opacity: 1.0 } },
        { id: "satellite_dish", name: "High-Gain Satellite Communication Dish", type: "column", layerId: "electrical", position: [5.5, 10.4, 0], dimensions: { width: 1.2, height: 0.2, depth: 1.2 }, material: { color: "#CBD5E1", opacity: 1.0 } },
      ],
    },
    plumbing: {
      id: "plumbing",
      name: "Plumbing System",
      visible: true,
      color: "#06B6D4",
      elements: [
        { id: "kitchen_faucet", name: "Matte Black Gooseneck Island Faucet", type: "pipe", layerId: "plumbing", position: [-4.5, 1.1, -2.5], dimensions: { width: 0.08, height: 0.35, depth: 0.15 }, material: { color: "#0F172A", opacity: 1.0 } },
        { id: "soaking_tub", name: "Freestanding Acrylic Soaking Tub", type: "fixture", layerId: "plumbing", position: [4.0, 4.0, -2.5], dimensions: { width: 1.8, height: 0.65, depth: 0.95 }, material: { color: "#F8FAFC", opacity: 1.0 } },
        { id: "double_vanity", name: "Floating Double Vanity with LED Mirror", type: "fixture", layerId: "plumbing", position: [4.0, 4.1, 0], dimensions: { width: 2.0, height: 0.85, depth: 0.6 }, material: { color: "#1E293B", opacity: 1.0 } },
        { id: "plumb_wet_stack", name: "Vertical 110mm PVC-U Soil & Vent Wet Stack", type: "pipe", layerId: "plumbing", position: [7.6, 3.6, -5.3], dimensions: { width: 0.22, height: 7.2, depth: 0.22 }, material: { color: "#06B6D4", opacity: 1.0 } },
      ],
    },
  },
};

export function sanitizeBuildingModel(raw: any): BuildingModel {
  if (!raw) return defaultVillaModel;

  // Unpack nested model if response wrapper is passed
  const target = raw.model && typeof raw.model === 'object' ? raw.model : raw;

  const result: BuildingModel = {
    id: typeof target.id === 'number' ? target.id : 1,
    name: target.name || "Custom Architectural Model",
    version: target.version || Date.now(),
    description: target.description || "",
    meta: target.meta || (raw.meta ? raw.meta : undefined),
    layers: {
      structural: { id: "structural", name: "Structural Layer", visible: true, color: "#D4FF32", elements: [] },
      electrical: { id: "electrical", name: "Electrical Layer", visible: true, color: "#F59E0B", elements: [] },
      plumbing: { id: "plumbing", name: "Plumbing Layer", visible: true, color: "#06B6D4", elements: [] },
    },
  };

  const sanitizeElement = (el: any, fallbackLayer = 'structural'): ModelElement => {
    const layer = (el.layerId || el.layer_id || fallbackLayer).toLowerCase();
    const cleanLayer = (layer.includes('elec') ? 'electrical' : layer.includes('plumb') ? 'plumbing' : 'structural');

    const pos = Array.isArray(el.position) && el.position.length >= 3
      ? [Number(el.position[0]) || 0, Number(el.position[1]) || 0, Number(el.position[2]) || 0] as [number, number, number]
      : [0, 0, 0] as [number, number, number];

    const dims = el.dimensions && typeof el.dimensions === 'object'
      ? {
          width: Math.max(0.05, Number(el.dimensions.width) || 1),
          height: Math.max(0.05, Number(el.dimensions.height) || 1),
          depth: Math.max(0.05, Number(el.dimensions.depth) || 1),
        }
      : { width: 1, height: 1, depth: 1 };

    return {
      id: String(el.id || `el_${Math.random().toString(36).substring(2, 9)}`),
      name: String(el.name || `${cleanLayer} element`),
      type: String(el.type || 'wall'),
      layerId: cleanLayer,
      position: pos,
      dimensions: dims,
      material: {
        color: el.material?.color || (cleanLayer === 'electrical' ? '#F59E0B' : cleanLayer === 'plumbing' ? '#06B6D4' : '#E2E8F0'),
        opacity: typeof el.material?.opacity === 'number' ? el.material.opacity : 1.0,
        roughness: typeof el.material?.roughness === 'number' ? el.material.roughness : 0.5,
        metalness: typeof el.material?.metalness === 'number' ? el.material.metalness : 0.1,
        transmission: typeof el.material?.transmission === 'number' ? el.material.transmission : 0.0,
      },
    };
  };

  if (raw.layers && typeof raw.layers === 'object') {
    for (const [key, layer] of Object.entries(raw.layers as Record<string, any>)) {
      const cleanKey = (key.includes('elec') ? 'electrical' : key.includes('plumb') ? 'plumbing' : 'structural');
      if (layer && Array.isArray(layer.elements)) {
        layer.elements.forEach((el: any) => {
          result.layers[cleanKey].elements.push(sanitizeElement(el, cleanKey));
        });
      }
    }
    return result;
  }

  const rawElements = Array.isArray(raw)
    ? raw
    : Array.isArray(raw.generated_elements)
    ? raw.generated_elements
    : Array.isArray(raw.elements)
    ? raw.elements
    : [];

  if (rawElements.length > 0) {
    rawElements.forEach((el: any) => {
      const cleanEl = sanitizeElement(el);
      result.layers[cleanEl.layerId as 'structural' | 'electrical' | 'plumbing'].elements.push(cleanEl);
    });
    return result;
  }

  return defaultVillaModel;
}

export async function fetchProjectModel(projectId = 1): Promise<BuildingModel> {
  try {
    const res = await fetch(`${API_BASE_URL}/projects/${projectId}/model`);
    if (!res.ok) throw new Error('API fetch failed');
    const data = await res.json();
    return sanitizeBuildingModel(data);
  } catch (err) {
    console.warn('Backend unavailable, using default AAA Villa Model:', err);
    return defaultVillaModel;
  }
}

export async function generateBimLayout(projectId: number, prompt: string): Promise<BuildingModel> {
  try {
    const res = await fetch(`${API_BASE_URL}/chat/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, prompt }),
    });
    if (!res.ok) throw new Error('AI Generation failed');
    const data = await res.json();
    return sanitizeBuildingModel(data);
  } catch (err) {
    console.error('generateBimLayout failed:', err);
    return defaultVillaModel;
  }
}
