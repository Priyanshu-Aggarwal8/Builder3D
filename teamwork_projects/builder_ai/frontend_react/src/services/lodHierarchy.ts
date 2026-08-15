import { BuildingModel } from '../types/model';
import { defaultVillaModel } from './api';

export type LodLevel = 'city' | 'society' | 'building' | 'storey' | 'apartment' | 'mep';

export interface LodNode {
  id: LodLevel;
  label: string;
  sublabel: string;
  cameraDistance: number;
  cameraHeight: number;
  description: string;
}

export const LOD_HIERARCHY: LodNode[] = [
  {
    id: 'city',
    label: 'City Massing',
    sublabel: 'LOD 100 • Urban District',
    cameraDistance: 120,
    cameraHeight: 70,
    description: 'Urban context, plot boundary setbacks, surrounding massing envelopes, and solar incidence.',
  },
  {
    id: 'society',
    label: 'Society Masterplan',
    sublabel: 'LOD 200 • Campus Masterplan',
    cameraDistance: 70,
    cameraHeight: 40,
    description: 'Multi-building development: Tower A, Commercial Tower B, Luxury Villas, Clubhouse & Central Green.',
  },
  {
    id: 'building',
    label: 'Building Envelope',
    sublabel: 'LOD 300 • OpenBIM Structure',
    cameraDistance: 32,
    cameraHeight: 18,
    description: 'Exterior facade, reinforced concrete columns, floor slabs, balconies, and machine room penthouse.',
  },
  {
    id: 'storey',
    label: 'Storey Level',
    sublabel: 'LOD 350 • Story Partitioning',
    cameraDistance: 24,
    cameraHeight: 14,
    description: 'Structural floor slabs, corridor circulation, interior partition matrix, and vertical core shafts.',
  },
  {
    id: 'apartment',
    label: 'Unit Interiors',
    sublabel: 'LOD 400 • Furnished 2BHK / 3BHK',
    cameraDistance: 16,
    cameraHeight: 8,
    description: 'Modular kitchen island, living room lounge, king master bedroom suite, and bath fixtures.',
  },
  {
    id: 'mep',
    label: 'MEP Engineering',
    sublabel: 'LOD 500 • MagiCAD Systems',
    cameraDistance: 28,
    cameraHeight: 16,
    description: 'DN110 sanitary wet stacks, 415V electrical busbar conduits, and rooftop HVAC distribution.',
  },
];

// 1. LOD 100: City District Context Model
export const cityDistrictModel: BuildingModel = {
  id: 101,
  name: "Metropolitan District Context (LOD 100)",
  version: Date.now(),
  description: "City-scale massing with surrounding urban commercial high-rises and transit corridors.",
  layers: {
    structural: {
      id: "structural",
      name: "Urban Massing & Terrain",
      visible: true,
      color: "#000000",
      elements: [
        { id: "city_terrain_base", name: "Metropolitan Ground Plane (140x140m)", type: "slab", layerId: "structural", position: [0, -0.4, 0], dimensions: { width: 140, height: 0.4, depth: 140 }, material: { color: "#0F172A", roughness: 0.95 } },
        { id: "road_main_ns", name: "Grand North-South Boulevard", type: "slab", layerId: "structural", position: [0, 0.05, 0], dimensions: { width: 16, height: 0.1, depth: 140 }, material: { color: "#1E293B", roughness: 0.9 } },
        { id: "road_cross", name: "East-West Cross Avenue", type: "slab", layerId: "structural", position: [0, 0.05, 0], dimensions: { width: 140, height: 0.1, depth: 14 }, material: { color: "#1E293B", roughness: 0.9 } },
        { id: "mass_tower_1", name: "Commercial Tower 1 (45-Story Massing)", type: "wall", layerId: "structural", position: [-35, 25, -35], dimensions: { width: 22, height: 50, depth: 22 }, material: { color: "#1E293B", opacity: 0.85 } },
        { id: "mass_tower_2", name: "Residential High-Rise (32-Story Massing)", type: "wall", layerId: "structural", position: [35, 18, -35], dimensions: { width: 20, height: 36, depth: 20 }, material: { color: "#1E293B", opacity: 0.85 } },
        { id: "mass_tower_3", name: "Hotel & Convention Center (20-Story)", type: "wall", layerId: "structural", position: [35, 12, 35], dimensions: { width: 26, height: 24, depth: 26 }, material: { color: "#1E293B", opacity: 0.85 } },
        { id: "mass_tower_4", name: "Mixed-Use Podium & Retail Hub", type: "wall", layerId: "structural", position: [-35, 8, 35], dimensions: { width: 28, height: 16, depth: 28 }, material: { color: "#1E293B", opacity: 0.85 } },
        { id: "target_plot_base", name: "Target Development Parcel (Plot #A4)", type: "slab", layerId: "structural", position: [0, 0.15, 0], dimensions: { width: 28, height: 0.3, depth: 26 }, material: { color: "#000000", opacity: 0.4 } },
        { id: "target_building_core", name: "Building Massing Envelope", type: "wall", layerId: "structural", position: [0, 5.0, 0], dimensions: { width: 18, height: 10, depth: 16 }, material: { color: "#0F172A", opacity: 0.9 } },
      ],
    },
    electrical: {
      id: "electrical",
      name: "Grid Conduits",
      visible: true,
      color: "#F59E0B",
      elements: [
        { id: "city_substation", name: "District 11kV Electrical Substation", type: "fixture", layerId: "electrical", position: [-18, 1.5, -18], dimensions: { width: 4, height: 3, depth: 4 }, material: { color: "#F59E0B" } }
      ]
    },
    plumbing: {
      id: "plumbing",
      name: "Municipal Water Main",
      visible: true,
      color: "#06B6D4",
      elements: [
        { id: "city_water_main", name: "Municipal 300mm Water Supply Trunk", type: "pipe", layerId: "plumbing", position: [0, -0.3, 8], dimensions: { width: 0.6, height: 80, depth: 0.6 }, material: { color: "#06B6D4" } }
      ]
    }
  }
};

// 2. LOD 200: Society & Campus Masterplan Model
export const societyCampusModel: BuildingModel = {
  id: 102,
  name: "Gated Community Society Masterplan (LOD 200)",
  version: Date.now(),
  description: "Society masterplan with Residential Tower A, Commercial Wing, and Central Green.",
  layers: {
    structural: {
      id: "structural",
      name: "Masterplan Grounds & Buildings",
      visible: true,
      color: "#000000",
      elements: [
        { id: "campus_ground", name: "Society Boundary Podium (90x80m)", type: "slab", layerId: "structural", position: [0, -0.3, 0], dimensions: { width: 90, height: 0.35, depth: 80 }, material: { color: "#0F172A", roughness: 0.9 } },
        { id: "internal_loop_road", name: "Internal Paved Driveway Loop", type: "slab", layerId: "structural", position: [0, 0.05, 0], dimensions: { width: 70, height: 0.08, depth: 60 }, material: { color: "#1E293B", roughness: 0.85 } },
        { id: "central_park_lawn", name: "Central Landscape Park & Lawn", type: "slab", layerId: "structural", position: [0, 0.12, 0], dimensions: { width: 35, height: 0.1, depth: 30 }, material: { color: "#15803D", roughness: 0.95 } },
        { id: "tower_a_mass", name: "Residential Tower A (18-Story)", type: "wall", layerId: "structural", position: [-22, 14, -18], dimensions: { width: 14, height: 28, depth: 14 }, material: { color: "#334155" } },
        { id: "tower_b_mass", name: "Commercial Office Tower B (12-Story)", type: "wall", layerId: "structural", position: [22, 10, -18], dimensions: { width: 14, height: 20, depth: 14 }, material: { color: "#334155" } },
        { id: "clubhouse_podium", name: "Community Clubhouse & Sports Deck", type: "wall", layerId: "structural", position: [22, 4, 18], dimensions: { width: 18, height: 8, depth: 14 }, material: { color: "#475569" } },
        { id: "target_estate_parcel", name: "Target Project Location (Plot #1)", type: "slab", layerId: "structural", position: [-22, 0.15, 18], dimensions: { width: 20, height: 0.25, depth: 18 }, material: { color: "#000000", opacity: 0.5 } },
      ],
    },
    electrical: {
      id: "electrical",
      name: "Campus Distribution",
      visible: true,
      color: "#F59E0B",
      elements: [
        { id: "campus_transformer", name: "Society Step-Down Transformer Station", type: "fixture", layerId: "electrical", position: [-32, 1.2, -30], dimensions: { width: 3, height: 2.4, depth: 3 }, material: { color: "#F59E0B" } }
      ]
    },
    plumbing: {
      id: "plumbing",
      name: "Site Water Distribution",
      visible: true,
      color: "#06B6D4",
      elements: [
        { id: "site_irrigation", name: "Automated Park Irrigation Distribution", type: "pipe", layerId: "plumbing", position: [0, 0.2, -5], dimensions: { width: 0.15, height: 20, depth: 0.15 }, material: { color: "#06B6D4" } }
      ]
    }
  }
};

export function getModelForLod(lod: LodLevel, activeBuildingModel: BuildingModel): BuildingModel {
  if (lod === 'city') return cityDistrictModel;
  if (lod === 'society') return societyCampusModel;
  return activeBuildingModel || defaultVillaModel;
}
