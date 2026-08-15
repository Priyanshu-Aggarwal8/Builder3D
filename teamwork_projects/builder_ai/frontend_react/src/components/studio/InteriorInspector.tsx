import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Palette, Home, CheckCircle2, ShieldCheck, Ruler, Layers,
  Copy, Trash2, Plus, Minus, X, ArrowRight, Wand2, Lightbulb, Sofa, Sliders,
  Maximize2, Move, Box
} from 'lucide-react';
import { ModelElement, BuildingModel } from '../../types/model';

interface InteriorInspectorProps {
  element: ModelElement | null;
  model: BuildingModel | null;
  onClose: () => void;
  onUpdateElementPosition: (id: string, axis: 0 | 1 | 2, delta: number) => void;
  onUpdateElementDimension: (id: string, dim: 'width' | 'depth' | 'height', delta: number) => void;
  onUpdateElementMaterialColor: (id: string, color: string) => void;
  onDuplicate: (el: ModelElement) => void;
  onDelete: (id: string) => void;
  onApplyNewModel: (m: BuildingModel) => void;
  isLightMode?: boolean;
}

export const InteriorInspector: React.FC<InteriorInspectorProps> = ({
  element,
  model,
  onClose,
  onUpdateElementPosition,
  onUpdateElementDimension,
  onUpdateElementMaterialColor,
  onDuplicate,
  onDelete,
  onApplyNewModel,
  isLightMode = false,
}) => {
  const [activeTab, setActiveTab] = useState<'design' | 'specs' | 'ai'>('design');
  const [selectedStyle, setSelectedStyle] = useState(model?.meta?.style || 'Japandi Scandinavian');

  // Real model statistics
  const totalElements = model?.layers
    ? Object.values(model.layers).reduce((acc, l) => acc + (l.elements || []).length, 0)
    : 0;
  const floors = model?.meta?.floors || 12;
  const grossArea = floors * 420;

  // Dynamic Styles definitions
  const interiorStyles = [
    {
      id: 'Japandi Scandinavian',
      name: 'Japandi Scandinavian',
      desc: 'Light oak timber, fluted acoustic paneling, linen fabrics',
      primaryColor: '#E0B88A',
      wallColor: '#F5EBE0',
      furnitureColor: '#D6C7B2',
    },
    {
      id: 'Luxury Calacatta',
      name: 'Luxury Calacatta',
      desc: 'Italian white marble, brushed bronze trim, velvet upholstery',
      primaryColor: '#F8FAFC',
      wallColor: '#EDE9FE',
      furnitureColor: '#1E293B',
    },
    {
      id: 'Industrial Loft',
      name: 'Industrial Loft',
      desc: 'Exposed clay brick, matte steel, polished architectural screed',
      primaryColor: '#B45309',
      wallColor: '#334155',
      furnitureColor: '#0F172A',
    },
    {
      id: 'Biophilic Green',
      name: 'Biophilic Green',
      desc: 'Living moss feature walls, natural teak, travertine stone',
      primaryColor: '#15803D',
      wallColor: '#E2E8F0',
      furnitureColor: '#78350F',
    },
  ];

  const handleApplyStylePreset = (styleId: string) => {
    if (!model || !model.layers) return;
    const styleObj = interiorStyles.find((s) => s.id === styleId);
    if (!styleObj) return;

    setSelectedStyle(styleId);
    const newLayers = { ...model.layers };

    // Apply color finishes dynamically across structural elements
    if (newLayers.structural && newLayers.structural.elements) {
      newLayers.structural.elements = newLayers.structural.elements.map((el) => {
        const nameLower = el.name.toLowerCase();
        let newColor = el.material?.color;

        if (nameLower.includes('sofa') || nameLower.includes('bed') || nameLower.includes('chair') || nameLower.includes('lounge')) {
          newColor = styleObj.furnitureColor;
        } else if (nameLower.includes('floor') || nameLower.includes('finish') || nameLower.includes('deck')) {
          newColor = styleObj.primaryColor;
        } else if (nameLower.includes('wall') || nameLower.includes('facade') || nameLower.includes('kitchen')) {
          newColor = styleObj.wallColor;
        }

        return {
          ...el,
          material: {
            ...(el.material || {}),
            color: newColor,
          },
        };
      });
    }

    onApplyNewModel({
      ...model,
      meta: { ...(model.meta || {}), style: styleId },
      layers: newLayers,
    });
  };

  if (!element) {
    return (
      <div className={`flex flex-col gap-4 text-xs ${isLightMode ? 'text-neutral-700' : 'text-neutral-300'}`}>
        <div className="flex items-center justify-between border-b pb-3 border-neutral-200 dark:border-neutral-800">
          <div className="flex items-center gap-2 font-black text-xs uppercase tracking-wider">
            <Home className="w-4 h-4 stroke-[2]" />
            <span>Building & Floor Specs</span>
          </div>
          <button onClick={onClose} className="opacity-60 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className={`p-3.5 rounded-2xl border flex flex-col gap-2 ${
          isLightMode ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
        }`}>
          <div className="flex justify-between py-1 border-b border-neutral-200 dark:border-neutral-800">
            <span>Project Model:</span>
            <span className="font-bold">{model?.name}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-200 dark:border-neutral-800">
            <span>Total Stories:</span>
            <span className="font-mono font-bold">{floors} Levels</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-200 dark:border-neutral-800">
            <span>Gross Floor Area:</span>
            <span className="font-mono font-bold">{grossArea.toLocaleString()} m²</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-200 dark:border-neutral-800">
            <span>BIM Entities:</span>
            <span className="font-mono font-bold">{totalElements} Components</span>
          </div>
          <div className="flex justify-between py-1">
            <span>Active Interior Aesthetic:</span>
            <span className="font-bold">{selectedStyle}</span>
          </div>
        </div>

        {/* Dynamic Interior Finishes Selector */}
        <div className="flex flex-col gap-2.5">
          <span className="text-[10px] font-black tracking-wider uppercase opacity-60">
            Interior Aesthetic Theme
          </span>
          <div className="grid grid-cols-2 gap-2">
            {interiorStyles.map((style) => (
              <button
                key={style.id}
                onClick={() => handleApplyStylePreset(style.id)}
                className={`p-3 rounded-2xl border text-left flex flex-col gap-1 transition-all ${
                  selectedStyle === style.id
                    ? isLightMode
                      ? 'border-black bg-neutral-100 shadow-sm'
                      : 'border-white bg-neutral-800 shadow-sm'
                    : isLightMode
                    ? 'bg-white border-neutral-200 hover:border-neutral-400'
                    : 'bg-neutral-950 border-neutral-800 hover:border-neutral-700'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full border border-black/20" style={{ backgroundColor: style.primaryColor }} />
                  <span className="font-bold text-xs">{style.name.split(' ')[0]}</span>
                </div>
                <span className="text-[10px] opacity-60 line-clamp-1">{style.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <div className={`p-3 rounded-xl border text-[11px] flex items-center gap-2.5 ${
          isLightMode ? 'bg-neutral-100 border-neutral-200 text-neutral-800' : 'bg-neutral-900 border-neutral-800 text-neutral-300'
        }`}>
          <Lightbulb className="w-4 h-4 shrink-0 stroke-[1.75]" />
          <span>Click any wall, room slab, door, or furniture piece in the 3D viewport to edit its dimensions, position, or material finish.</span>
        </div>
      </div>
    );
  }

  // Active Element Selected Inspector
  const [posX, posY, posZ] = element.position;
  const { width, height, depth } = element.dimensions;

  return (
    <div className={`flex flex-col gap-4 text-xs ${isLightMode ? 'text-neutral-800' : 'text-neutral-200'}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-3 border-neutral-200 dark:border-neutral-800">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider font-mono opacity-60">
            {element.layerId} • {element.type}
          </span>
          <span className="font-black text-sm truncate max-w-[200px]">
            {element.name}
          </span>
        </div>
        <button onClick={onClose} className="opacity-60 hover:opacity-100 p-1">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className={`flex items-center p-1 rounded-xl border ${
        isLightMode ? 'bg-neutral-100 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
      }`}>
        {(['design', 'specs', 'ai'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 py-1.5 rounded-lg text-xs font-bold capitalize transition-all ${
              activeTab === tab
                ? isLightMode
                  ? 'bg-black text-white shadow-sm'
                  : 'bg-white text-black shadow-sm'
                : isLightMode
                ? 'text-neutral-600 hover:text-black'
                : 'text-neutral-400 hover:text-white'
            }`}
          >
            {tab === 'ai' ? 'AI Finish' : tab}
          </button>
        ))}
      </div>

      {/* Tab 1: Design & Transforms */}
      {activeTab === 'design' && (
        <div className="flex flex-col gap-4">
          {/* Position Transform Controls */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-black uppercase tracking-wider opacity-60">Position [X, Y, Z] (Meters)</span>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'X (Lateral)', val: posX, axis: 0 as const },
                { label: 'Y (Elevation)', val: posY, axis: 1 as const },
                { label: 'Z (Depth)', val: posZ, axis: 2 as const },
              ].map((item) => (
                <div
                  key={item.label}
                  className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 ${
                    isLightMode ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
                  }`}
                >
                  <span className="text-[10px] opacity-60">{item.label}</span>
                  <span className="font-mono font-bold text-xs">
                    {item.val.toFixed(2)}m
                  </span>
                  <div className="flex items-center gap-1 w-full mt-1">
                    <button
                      onClick={() => onUpdateElementPosition(element.id, item.axis, -0.2)}
                      className={`flex-1 py-1 rounded text-center font-bold text-xs border transition-all ${
                        isLightMode
                          ? 'bg-white border-neutral-300 text-black hover:bg-neutral-100'
                          : 'bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700'
                      }`}
                    >
                      -
                    </button>
                    <button
                      onClick={() => onUpdateElementPosition(element.id, item.axis, 0.2)}
                      className={`flex-1 py-1 rounded text-center font-bold text-xs border transition-all ${
                        isLightMode
                          ? 'bg-black text-white border-black hover:bg-neutral-800'
                          : 'bg-white text-black border-white hover:bg-neutral-200'
                      }`}
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Dimension Controls */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-black uppercase tracking-wider opacity-60">Dimensions (Width • Height • Depth)</span>
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'Width', val: width, key: 'width' as const },
                { label: 'Height', val: height, key: 'height' as const },
                { label: 'Depth', val: depth, key: 'depth' as const },
              ].map((item) => (
                <div
                  key={item.label}
                  className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 ${
                    isLightMode ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
                  }`}
                >
                  <span className="text-[10px] opacity-60">{item.label}</span>
                  <span className="font-mono font-bold text-xs">
                    {item.val.toFixed(2)}m
                  </span>
                  <div className="flex items-center gap-1 w-full mt-1">
                    <button
                      onClick={() => onUpdateElementDimension(element.id, item.key, -0.2)}
                      className={`flex-1 py-1 rounded text-center font-bold text-xs border transition-all ${
                        isLightMode
                          ? 'bg-white border-neutral-300 text-black hover:bg-neutral-100'
                          : 'bg-neutral-800 border-neutral-700 text-white hover:bg-neutral-700'
                      }`}
                    >
                      -
                    </button>
                    <button
                      onClick={() => onUpdateElementDimension(element.id, item.key, 0.2)}
                      className={`flex-1 py-1 rounded text-center font-bold text-xs border transition-all ${
                        isLightMode
                          ? 'bg-black text-white border-black hover:bg-neutral-800'
                          : 'bg-white text-black border-white hover:bg-neutral-200'
                      }`}
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Architectural Color & Finish Palette */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] font-black uppercase tracking-wider opacity-60">Material Finish Swatches</span>
            <div className="flex items-center gap-2 flex-wrap">
              {[
                '#FFFFFF', '#F5EBE0', '#E0B88A', '#78350F', '#1E293B',
                '#334155', '#475569', '#38BDF8', '#F59E0B', '#06B6D4'
              ].map((c) => (
                <button
                  key={c}
                  onClick={() => onUpdateElementMaterialColor(element.id, c)}
                  className={`w-7 h-7 rounded-full border-2 transition-transform hover:scale-125 shadow-sm ${
                    element.material?.color === c
                      ? (isLightMode ? 'border-black scale-110' : 'border-white scale-110')
                      : 'border-transparent'
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 pt-2 border-t border-neutral-200 dark:border-neutral-800">
            <button
              onClick={() => onDuplicate(element)}
              className={`flex-1 py-2 rounded-xl border flex items-center justify-center gap-1.5 font-bold transition-all ${
                isLightMode
                  ? 'bg-neutral-100 hover:bg-neutral-200 border-neutral-300 text-black'
                  : 'bg-neutral-900 hover:bg-neutral-800 border-neutral-800 text-white'
              }`}
            >
              <Copy className="w-3.5 h-3.5 stroke-[2]" />
              <span>Duplicate</span>
            </button>
            <button
              onClick={() => onDelete(element.id)}
              className="flex-1 py-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 hover:bg-red-500/20 flex items-center justify-center gap-1.5 font-bold transition-all"
            >
              <Trash2 className="w-3.5 h-3.5 stroke-[2]" />
              <span>Remove</span>
            </button>
          </div>
        </div>
      )}

      {/* Tab 2: Specs */}
      {activeTab === 'specs' && (
        <div className={`p-3.5 rounded-2xl border flex flex-col gap-2.5 ${
          isLightMode ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
        }`}>
          <div className="flex justify-between py-1 border-b border-neutral-200 dark:border-neutral-800">
            <span>Entity ID:</span>
            <span className="font-mono font-bold">{element.id}</span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-200 dark:border-neutral-800">
            <span>IFC Product Class:</span>
            <span className="font-mono font-bold">
              Ifc{element.type.charAt(0).toUpperCase() + element.type.slice(1)}
            </span>
          </div>
          <div className="flex justify-between py-1 border-b border-neutral-200 dark:border-neutral-800">
            <span>Component Volume:</span>
            <span className="font-mono font-bold">
              {(width * height * depth).toFixed(2)} m³
            </span>
          </div>
          <div className="flex justify-between py-1">
            <span>Surface Shader:</span>
            <span className="font-bold">PBR Architectural Matte</span>
          </div>
        </div>
      )}

      {/* Tab 3: AI Redesign */}
      {activeTab === 'ai' && (
        <div className="flex flex-col gap-3">
          <p className="text-[11px] opacity-70">
            Apply automated AI texture, finish, and spatial harmony to this component based on your design brief.
          </p>
          <div className="grid grid-cols-1 gap-2">
            {interiorStyles.map((style) => (
              <button
                key={style.id}
                onClick={() => onUpdateElementMaterialColor(element.id, style.furnitureColor)}
                className={`p-2.5 rounded-xl border text-left flex items-center justify-between transition-all ${
                  isLightMode
                    ? 'bg-neutral-50 border-neutral-200 hover:bg-neutral-100'
                    : 'bg-neutral-900 border-neutral-800 hover:bg-neutral-800'
                }`}
              >
                <div>
                  <div className="font-bold text-xs">{style.name}</div>
                  <div className="text-[10px] opacity-50">{style.desc}</div>
                </div>
                <div className="w-4 h-4 rounded-full border border-black/20" style={{ backgroundColor: style.furnitureColor }} />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
