export interface ModelElement {
  id: string;
  name: string;
  type: 'wall' | 'slab' | 'column' | 'window' | 'door' | 'pipe' | 'conduit' | 'light' | 'fixture' | string;
  layerId: string;
  position: [number, number, number]; // [x, y, z] in meters (Y is UP)
  rotation?: [number, number, number];
  scale?: [number, number, number];
  dimensions: {
    width: number;
    height: number;
    depth: number;
  };
  material?: {
    color?: string;
    opacity?: number;
    roughness?: number;
    metalness?: number;
    transmission?: number;
  };
  properties?: Record<string, any>;
}

export interface BuildingLayer {
  id: string;
  name: string;
  visible: boolean;
  color: string;
  elements: ModelElement[];
}

export interface BuildingModelMeta {
  floors?: number;
  style?: string;
  typology?: string;
  has_city?: boolean;
  has_society?: boolean;
  available_scales?: string[];
}

export interface BuildingModel {
  id: number;
  name: string;
  version?: number;
  description?: string;
  meta?: BuildingModelMeta;
  layers: Record<string, BuildingLayer>;
}

export type RenderMode = 'shaded' | 'wireframe' | 'xray';
export type ToolType = 'select' | 'orbit' | 'pan' | 'measure' | 'wall' | 'slab' | 'column' | 'conduit' | 'pipe';
export type CameraPreset = 'iso' | 'top' | 'front' | 'right';
