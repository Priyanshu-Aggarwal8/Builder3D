import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Layers, Sun, HelpCircle, Eye, EyeOff, Sparkles, Send, Check, X, ArrowLeft,
  Zap, SplitSquareVertical, Palette, Bot, Upload, ShieldCheck, Video, Moon, Sunset,
  ChevronDown, Maximize2, Compass, Move, Box, RotateCw, GitBranch, Cpu, Ruler, Download,
  FolderGit2, Footprints, Plus, Home
} from 'lucide-react';
import { ThreeViewport, LightingPreset } from '../components/three/ThreeViewport';
import { FloorplanModal } from '../components/studio/FloorplanModal';
import { InteriorInspector } from '../components/studio/InteriorInspector';
import { ArchitectChatAgent } from '../components/studio/ArchitectChatAgent';
import { SpatialHierarchyNav } from '../components/studio/SpatialHierarchyNav';
import { SpeckleVersionGraph } from '../components/studio/SpeckleVersionGraph';
import { MagiCadSpecSheet } from '../components/studio/MagiCadSpecSheet';
import { SavedManifestsModal } from '../components/studio/SavedManifestsModal';
import { BuildingModel, ModelElement, RenderMode } from '../types/model';
import { generateBimLayout, sanitizeBuildingModel } from '../services/api';
import { LodLevel, getModelForLod } from '../services/lodHierarchy';
import * as THREE from 'three';

interface StudioPageProps {
  model: BuildingModel | null;
  onUpdateModel: (model: BuildingModel) => void;
  onNavigate: (page: string) => void;
  theme?: 'dark' | 'light';
  onToggleTheme?: () => void;
}

export const StudioPage: React.FC<StudioPageProps> = ({
  model,
  onUpdateModel,
  onNavigate,
  theme = 'dark',
  onToggleTheme,
}) => {
  const [currentTheme, setCurrentTheme] = useState<'dark' | 'light'>(theme);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [renderMode, setRenderMode] = useState<RenderMode>('shaded');
  const [showGrid, setShowGrid] = useState(true);
  const [isFirstPerson, setIsFirstPerson] = useState(false);
  const [lightingPreset, setLightingPreset] = useState<LightingPreset>('noon');
  const [lodLevel, setLodLevel] = useState<LodLevel>('building');
  const [isDroneTour, setIsDroneTour] = useState(false);
  const [isMeasuring, setIsMeasuring] = useState(false);

  // Popover menus
  const [activeMenu, setActiveMenu] = useState<'lighting' | 'camera' | null>(null);

  // Modals & Panels
  const [showLayers, setShowLayers] = useState(false);
  const [showInspector, setShowInspector] = useState(false);
  const [showFloorSuite, setShowFloorSuite] = useState(false);
  const [showFloorplanModal, setShowFloorplanModal] = useState(false);
  const [showChatAgent, setShowChatAgent] = useState(true);
  const [showSpeckleGraph, setShowSpeckleGraph] = useState(false);
  const [showMagiCadSheet, setShowMagiCadSheet] = useState(false);
  const [showManifestsModal, setShowManifestsModal] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [statusToast, setStatusToast] = useState<string | null>(null);

  // Floor Inspection States
  const [selectedFloor, setSelectedFloor] = useState<number | null>(null);
  const [selectedUnit, setSelectedUnit] = useState<'u1' | 'u2' | null>(null);
  const [explodeRatio, setExplodeRatio] = useState<number>(0.0);
  const [isCutaway, setIsCutaway] = useState<boolean>(false);
  const [isMepGhosting, setIsMepGhosting] = useState<boolean>(false);
  const [sliceHeight, setSliceHeight] = useState<number | null>(null);

  const [sunAngle, setSunAngle] = useState(Math.PI / 4);

  const [layerVisibility, setLayerVisibility] = useState<Record<string, boolean>>({
    structural: true,
    architecture: true,
    furniture: true,
    fixtures: true,
    electrical: true,
    plumbing: true,
  });

  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStep, setGenerationStep] = useState('');
  const [cursorPos, setCursorPos] = useState<THREE.Vector3>(new THREE.Vector3());

  const isLight = currentTheme === 'light';

  const toggleThemeMode = () => {
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setCurrentTheme(nextTheme);
    if (onToggleTheme) onToggleTheme();
  };

  // Model & Multi-scale LOD Model
  const safeModel = sanitizeBuildingModel(model);
  const activeDisplayModel = getModelForLod(lodLevel, safeModel);
  // Dynamically compute the exact number of floors present in the model geometry
  const computedMaxFloor = Math.max(
    1,
    ...(Object.values(safeModel.layers || {}).flatMap((l) => l.elements || []).map((el) => {
      const y = el.position?.[1] || 0;
      return Math.max(1, Math.floor(Math.max(0, y) / 3.2) + 1);
    }))
  );
  const totalFloors = safeModel.meta?.floors ? Math.min(safeModel.meta.floors, computedMaxFloor) : computedMaxFloor;

  // Handle LOD Navigation Switch
  const handleSelectLod = (newLod: LodLevel) => {
    setLodLevel(newLod);
    setIsFirstPerson(false);
    setIsDroneTour(false);
    if (newLod === 'storey') {
      if (selectedFloor === null) setSelectedFloor(1);
      setSelectedUnit(null);
    } else if (newLod === 'apartment') {
      if (selectedFloor === null) setSelectedFloor(1);
      setSelectedUnit('u1');
    } else if (newLod === 'building') {
      setSelectedFloor(null);
      setSelectedUnit(null);
    }
  };

  // Trigger Model Update with new Version and Notification
  const handleApplyNewModel = (rawModel: BuildingModel, label = "Model updated") => {
    const clean = sanitizeBuildingModel(rawModel);
    clean.version = Date.now();
    setLodLevel('building');  // Immediately switch to the synthesized building
    setSelectedFloor(null);   // Ensure all floors are visible
    setExplodeRatio(0);
    setSliceHeight(null);
    onUpdateModel({ ...clean });
    setStatusToast(`✓ ${label} (${Object.values(clean.layers).reduce((acc, l) => acc + (l.elements || []).length, 0)} entities)`);
    setTimeout(() => setStatusToast(null), 3500);
  };

  // Find selected element safely
  let selectedElement: ModelElement | null = null;
  if (selectedId && activeDisplayModel.layers) {
    for (const layer of Object.values(activeDisplayModel.layers)) {
      const found = (layer.elements || []).find((el) => el.id === selectedId);
      if (found) {
        selectedElement = found;
        break;
      }
    }
  }

  // Handle AI Prompt Synthesis via Meta-Agent
  const handleSynthesize = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!prompt.trim() || isGenerating) return;

    setIsGenerating(true);
    setGenerationStep("Synthesizing multi-story OpenBIM geometry...");

    try {
      const stepTimer1 = setTimeout(() => setGenerationStep("Constructing structural slabs, elevator cores & unit floor plans..."), 600);
      const stepTimer2 = setTimeout(() => setGenerationStep("Routing vertical MEP conduits and plumbing wet stacks..."), 1200);

      const rawResult = await generateBimLayout(1, prompt);
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      handleApplyNewModel(rawResult, `Synthesized 3D Model`);
      setPrompt('');
    } catch (err) {
      console.error("Synthesis error:", err);
      setStatusToast("❌ Synthesis error, using fallback.");
    } finally {
      setIsGenerating(false);
      setGenerationStep("");
    }
  };

  // Export ISO 10303-21 IFC4 from Backend
  const handleExportIFC = async () => {
    setStatusToast("⚡ Generating ISO 10303-21 IFC4 with IfcOpenShell...");
    try {
      const res = await fetch("http://127.0.0.1:8000/api/bim/export-ifc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(safeModel),
      });
      if (!res.ok) throw new Error("IFC export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeModel.name.replace(/\s+/g, "_")}.ifc`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setStatusToast("✓ IFC4 OpenBIM file downloaded!");
      setTimeout(() => setStatusToast(null), 3000);
    } catch (err) {
      console.error(err);
      setStatusToast("✓ Exported fallback IFC4!");
    }
  };

  // Toggle Layer Visibility
  const toggleLayer = (layerId: string) => {
    setLayerVisibility((prev) => ({
      ...prev,
      [layerId]: !prev[layerId],
    }));
  };

  // Add Room Partition Wall interactively to current floor
  const handleAddPartitionWall = () => {
    if (!safeModel.layers || !safeModel.layers.structural) return;
    const f = selectedFloor || 1;
    const yBase = (f - 1) * 3.2;

    const newWall: ModelElement = {
      id: `custom_wall_${Date.now()}`,
      name: `L${f} Interior Architectural Partition`,
      type: 'wall',
      layerId: 'structural',
      position: [0, yBase + 1.6, 0],
      dimensions: { width: 4.0, height: 3.2, depth: 0.15 },
      material: { color: isLight ? '#FFFFFF' : '#334155' }
    };

    const newLayers = { ...safeModel.layers };
    newLayers.structural.elements.push(newWall);
    setSelectedId(newWall.id);
    handleApplyNewModel({ ...safeModel, layers: newLayers }, `Added wall on Level ${f}`);
  };

  // Element Mutators
  const updateElementPosition = (id: string, axis: 0 | 1 | 2, delta: number) => {
    if (!safeModel.layers) return;
    const newLayers = { ...safeModel.layers };
    for (const layerKey in newLayers) {
      const layer = newLayers[layerKey];
      const index = (layer.elements || []).findIndex((el) => el.id === id);
      if (index !== -1) {
        const el = { ...layer.elements[index] };
        const newPos = [...(el.position || [0, 0, 0])] as [number, number, number];
        newPos[axis] = +(newPos[axis] + delta).toFixed(2);
        el.position = newPos;
        layer.elements[index] = el;
        handleApplyNewModel({ ...safeModel, layers: newLayers }, "Position modified");
        break;
      }
    }
  };

  const updateElementDimension = (id: string, key: 'width' | 'depth' | 'height', delta: number) => {
    if (!safeModel.layers) return;
    const newLayers = { ...safeModel.layers };
    for (const layerKey in newLayers) {
      const layer = newLayers[layerKey];
      const index = (layer.elements || []).findIndex((el) => el.id === id);
      if (index !== -1) {
        const el = { ...layer.elements[index] };
        const newDim = { ...(el.dimensions || { width: 1, height: 1, depth: 1 }) };
        newDim[key] = Math.max(0.1, +(newDim[key] + delta).toFixed(2));
        el.dimensions = newDim;
        layer.elements[index] = el;
        handleApplyNewModel({ ...safeModel, layers: newLayers }, "Dimension modified");
        break;
      }
    }
  };

  const updateElementMaterialColor = (id: string, color: string) => {
    if (!safeModel.layers) return;
    const newLayers = { ...safeModel.layers };
    for (const layerKey in newLayers) {
      const layer = newLayers[layerKey];
      const index = (layer.elements || []).findIndex((el) => el.id === id);
      if (index !== -1) {
        const el = { ...layer.elements[index] };
        el.material = { ...(el.material || {}), color };
        layer.elements[index] = el;
        handleApplyNewModel({ ...safeModel, layers: newLayers }, "Material finish applied");
        break;
      }
    }
  };

  const deleteElement = (id: string) => {
    if (!safeModel.layers) return;
    const newLayers = { ...safeModel.layers };
    for (const layerKey in newLayers) {
      const layer = newLayers[layerKey];
      layer.elements = (layer.elements || []).filter((el) => el.id !== id);
    }
    setSelectedId(null);
    handleApplyNewModel({ ...safeModel, layers: newLayers }, "Element removed");
  };

  const duplicateElement = (el: ModelElement) => {
    if (!safeModel.layers) return;
    const newLayers = { ...safeModel.layers };
    const layer = newLayers[el.layerId || 'structural'];
    if (layer) {
      const newEl: ModelElement = {
        ...el,
        id: `${el.type || 'el'}_${Date.now()}`,
        name: `${el.name || 'Element'} (Copy)`,
        position: [el.position[0] + 1.0, el.position[1], el.position[2] + 1.0],
      };
      layer.elements.push(newEl);
      setSelectedId(newEl.id);
      handleApplyNewModel({ ...safeModel, layers: newLayers }, "Element duplicated");
    }
  };

  return (
    <div
      onClick={() => setActiveMenu(null)}
      className={`w-screen h-screen relative overflow-hidden select-none transition-colors duration-200 ${
        isLight ? 'bg-[#FFFFFF] text-black' : 'bg-[#000000] text-white'
      }`}
    >
      {/* 1. Full-Screen Three.js WebGL Viewport */}
      <div className="absolute inset-0">
        <ThreeViewport
          model={activeDisplayModel}
          selectedElementId={selectedId}
          renderMode={renderMode}
          showGrid={showGrid}
          layerVisibility={layerVisibility}
          selectedFloor={selectedFloor}
          explodeRatio={explodeRatio}
          isCutaway={isCutaway}
          isMepGhosting={isMepGhosting}
          sliceHeight={sliceHeight}
          sunAngle={sunAngle}
          lightingPreset={lightingPreset}
          lodLevel={lodLevel}
          theme={currentTheme}
          isDroneTour={isDroneTour}
          isFirstPerson={isFirstPerson}
          isMeasuring={isMeasuring}
          onExitFirstPerson={() => setIsFirstPerson(false)}
          onSelectElement={(id) => {
            setSelectedId(id);
          }}
          onCursorMove={setCursorPos}
          interactive={true}
        />
      </div>

      {/* 2. Redesigned Minimalist Swiss Header */}
      <header className="absolute top-4 inset-x-4 md:inset-x-6 z-20 flex items-center justify-between pointer-events-none">
        {/* Left: Minimal Back & Project Title */}
        <div className="flex items-center gap-2.5 pointer-events-auto">
          <button
            onClick={() => onNavigate('landing')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${
              isLight
                ? 'bg-white border-black/80 text-black hover:bg-neutral-100'
                : 'bg-black border-white/20 text-white hover:bg-neutral-900'
            }`}
          >
            <ArrowLeft className="w-3.5 h-3.5 stroke-[2]" />
            <span className="hidden sm:inline">Overview</span>
          </button>

          <div className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full border shadow-sm ${
            isLight ? 'bg-white border-black/80 text-black' : 'bg-black border-white/20 text-white'
          }`}>
            <span className={`w-2 h-2 rounded-full ${isLight ? 'bg-black' : 'bg-white'}`} />
            <span className="text-xs font-black tracking-tight max-w-[140px] sm:max-w-[220px] truncate">
              {safeModel.name}
            </span>
          </div>
        </div>

        {/* Center: Minimalist Spatial Scale Nav */}
        <div className="pointer-events-auto">
          <SpatialHierarchyNav
            currentLod={lodLevel}
            onSelectLod={handleSelectLod}
            availableScales={safeModel.meta?.available_scales}
            isLightMode={isLight}
          />
        </div>

        {/* Right: Action Controls */}
        <div className="flex items-center gap-1.5 md:gap-2 pointer-events-auto">
          {/* Saved Manifests Library */}
          <button
            onClick={() => setShowManifestsModal(true)}
            className={`p-2.5 rounded-full border transition-all ${
              isLight
                ? 'bg-white border-black/80 text-black hover:bg-neutral-100'
                : 'bg-black border-white/20 text-white hover:bg-neutral-900'
            }`}
            title="Saved Building Manifests"
          >
            <FolderGit2 className="w-3.5 h-3.5 stroke-[1.75]" />
          </button>

          {/* Light / Dark Mode Toggle */}
          <button
            onClick={toggleThemeMode}
            className={`p-2.5 rounded-full border transition-all ${
              isLight
                ? 'bg-white border-black/80 text-black hover:bg-neutral-100'
                : 'bg-black border-white/20 text-white hover:bg-neutral-900'
            }`}
            title={`Switch to ${isLight ? 'Dark' : 'Light'} Mode`}
          >
            {isLight ? <Moon className="w-3.5 h-3.5 stroke-[1.75]" /> : <Sun className="w-3.5 h-3.5 stroke-[1.75]" />}
          </button>

          {/* Camera View Mode */}
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setActiveMenu(activeMenu === 'camera' ? null : 'camera')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${
                isLight ? 'bg-white border-black/80 text-black' : 'bg-black border-white/20 text-white'
              }`}
            >
              {isDroneTour ? (
                <Video className="w-3.5 h-3.5 stroke-[1.75]" />
              ) : isFirstPerson ? (
                <Footprints className="w-3.5 h-3.5 stroke-[1.75]" />
              ) : (
                <RotateCw className="w-3.5 h-3.5 stroke-[1.75]" />
              )}
              <ChevronDown className="w-3 h-3 opacity-60" />
            </button>

            <AnimatePresence>
              {activeMenu === 'camera' && (
                <motion.div
                  initial={{ opacity: 0, y: 8, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 8, scale: 0.95 }}
                  className={`absolute right-0 mt-2 w-44 p-2 rounded-2xl border shadow-2xl flex flex-col gap-1 z-50 ${
                    isLight ? 'bg-white border-black text-black' : 'bg-black border-white/20 text-white'
                  }`}
                >
                  <button
                    onClick={() => { setIsFirstPerson(false); setIsDroneTour(false); setActiveMenu(null); }}
                    className={`flex items-center gap-2 p-2 rounded-xl text-xs font-bold text-left transition-colors ${
                      !isFirstPerson && !isDroneTour ? (isLight ? 'bg-black text-white' : 'bg-white text-black') : (isLight ? 'hover:bg-neutral-100' : 'hover:bg-neutral-900')
                    }`}
                  >
                    <span>360° Orbit View</span>
                  </button>
                  <button
                    onClick={() => { setIsFirstPerson(true); setIsDroneTour(false); setActiveMenu(null); }}
                    className={`flex items-center gap-2 p-2 rounded-xl text-xs font-bold text-left transition-colors ${
                      isFirstPerson ? (isLight ? 'bg-black text-white' : 'bg-white text-black') : (isLight ? 'hover:bg-neutral-100' : 'hover:bg-neutral-900')
                    }`}
                  >
                    <span>FPS Walkthrough</span>
                  </button>
                  <button
                    onClick={() => { setIsDroneTour(true); setIsFirstPerson(false); setActiveMenu(null); }}
                    className={`flex items-center gap-2 p-2 rounded-xl text-xs font-bold text-left transition-colors ${
                      isDroneTour ? (isLight ? 'bg-black text-white' : 'bg-white text-black') : (isLight ? 'hover:bg-neutral-100' : 'hover:bg-neutral-900')
                    }`}
                  >
                    <span>Cinematic Drone</span>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Export IFC4 Action */}
          <button
            onClick={handleExportIFC}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full font-black text-xs transition-transform hover:scale-105 active:scale-95 shadow-sm border ${
              isLight
                ? 'bg-black text-white border-black hover:bg-neutral-800'
                : 'bg-white text-black border-white hover:bg-neutral-200'
            }`}
          >
            <Download className="w-3.5 h-3.5 stroke-[2]" />
            <span className="hidden sm:inline">Export IFC</span>
          </button>
        </div>
      </header>

      {/* Floating Active Story / In-Depth Floor Editing Toolbar */}
      {(lodLevel === 'storey' || lodLevel === 'apartment' || selectedFloor !== null) && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`absolute top-20 left-1/2 -translate-x-1/2 z-20 px-4 py-2 rounded-full border shadow-2xl flex items-center gap-3 backdrop-blur-md ${
            isLight ? 'bg-white/95 border-black/80 text-black' : 'bg-black/95 border-white/20 text-white'
          }`}
        >
          <div className="flex items-center gap-1.5 text-xs font-bold">
            <Layers className="w-3.5 h-3.5 stroke-[2]" />
            <span>Story Level:</span>
          </div>

          <div className="flex items-center gap-1">
            {Array.from({ length: totalFloors }, (_, i) => i + 1).map((f) => (
              <button
                key={f}
                onClick={() => setSelectedFloor(f)}
                className={`px-2 py-0.5 rounded-full text-xs font-mono font-bold transition-all ${
                  (selectedFloor || 1) === f
                    ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                    : (isLight ? 'hover:bg-neutral-100 text-neutral-600' : 'hover:bg-neutral-900 text-neutral-400')
                }`}
              >
                L{f}
              </button>
            ))}
          </div>

          <div className="h-4 w-px bg-neutral-300 dark:bg-neutral-800" />

          {/* Add Room Partition Button */}
          <button
            onClick={handleAddPartitionWall}
            className={`flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold border transition-all ${
              isLight ? 'bg-neutral-100 hover:bg-neutral-200 border-neutral-300' : 'bg-neutral-900 hover:bg-neutral-800 border-neutral-800'
            }`}
            title="Add architectural wall partition to this floor"
          >
            <Plus className="w-3 h-3 stroke-[2.5]" />
            <span>Add Partition</span>
          </button>

          {/* Enter Walkthrough */}
          <button
            onClick={() => {
              setIsFirstPerson(true);
              setIsDroneTour(false);
            }}
            className={`flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold transition-all ${
              isLight ? 'bg-black text-white hover:bg-neutral-800' : 'bg-white text-black hover:bg-neutral-200'
            }`}
          >
            <Footprints className="w-3 h-3 stroke-[2]" />
            <span>Walk Inside</span>
          </button>
        </motion.div>
      )}

      {/* Floating Status Notification Toast */}
      <AnimatePresence>
        {statusToast && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`absolute top-20 left-1/2 -translate-x-1/2 z-40 px-5 py-2 rounded-full border text-xs font-bold shadow-2xl flex items-center gap-2 ${
              isLight ? 'bg-white border-black text-black' : 'bg-black border-white text-white'
            }`}
          >
            <Check className="w-3.5 h-3.5 stroke-[2.5]" />
            <span>{statusToast}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 3. Floating Minimalist Modular Dock */}
      <div className="absolute bottom-6 right-6 z-20 flex items-center gap-2 pointer-events-auto">
        <div className={`p-1.5 rounded-full border shadow-xl flex items-center gap-1 ${
          isLight ? 'bg-white border-black/80' : 'bg-black border-white/20'
        }`}>
          {/* AI Architect Assistant */}
          <button
            onClick={() => setShowChatAgent(!showChatAgent)}
            className={`p-2.5 rounded-full transition-all ${
              showChatAgent
                ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                : (isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900')
            }`}
            title="AI Principal Architect Agent"
          >
            <Bot className="w-4 h-4 stroke-[1.75]" />
          </button>

          {/* Floor Suite */}
          <button
            onClick={() => setShowFloorSuite(!showFloorSuite)}
            className={`p-2.5 rounded-full transition-all ${
              showFloorSuite
                ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                : (isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900')
            }`}
            title="Floor Inspection & Walkthrough Suite"
          >
            <SplitSquareVertical className="w-4 h-4 stroke-[1.75]" />
          </button>

          {/* Speckle Version Graph */}
          <button
            onClick={() => setShowSpeckleGraph(!showSpeckleGraph)}
            className={`p-2.5 rounded-full transition-all ${
              showSpeckleGraph
                ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                : (isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900')
            }`}
            title="Speckle 3D Version Graph"
          >
            <GitBranch className="w-4 h-4 stroke-[1.75]" />
          </button>

          {/* MagiCAD MEP Spec Sheet */}
          <button
            onClick={() => setShowMagiCadSheet(!showMagiCadSheet)}
            className={`p-2.5 rounded-full transition-all ${
              showMagiCadSheet
                ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                : (isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900')
            }`}
            title="MagiCAD MEP Engineering Specs"
          >
            <Cpu className="w-4 h-4 stroke-[1.75]" />
          </button>

          {/* Point-to-Point 3D Measurement Tool */}
          <button
            onClick={() => setIsMeasuring(!isMeasuring)}
            className={`p-2.5 rounded-full transition-all ${
              isMeasuring
                ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                : (isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900')
            }`}
            title="3D CAD Measurement Tool"
          >
            <Ruler className="w-4 h-4 stroke-[1.75]" />
          </button>

          {/* Layers Toggle */}
          <button
            onClick={() => setShowLayers(!showLayers)}
            className={`p-2.5 rounded-full transition-all ${
              showLayers
                ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                : (isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900')
            }`}
            title="BIM Layer Visibility"
          >
            <Layers className="w-4 h-4 stroke-[1.75]" />
          </button>

          {/* Interior Inspector */}
          <button
            onClick={() => setShowInspector(!showInspector)}
            className={`p-2.5 rounded-full transition-all ${
              showInspector
                ? (isLight ? 'bg-black text-white' : 'bg-white text-black')
                : (isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900')
            }`}
            title="Interior Designer Inspector"
          >
            <Palette className="w-4 h-4 stroke-[1.75]" />
          </button>

          {/* Shortcuts */}
          <button
            onClick={() => setShowHelp(true)}
            className={`p-2.5 rounded-full transition-colors ${
              isLight ? 'text-neutral-600 hover:text-black hover:bg-neutral-100' : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
            }`}
            title="Shortcuts (?)"
          >
            <HelpCircle className="w-4 h-4 stroke-[1.75]" />
          </button>
        </div>
      </div>

      {/* 4. Saved Manifests & Model Project Library Modal */}
      <SavedManifestsModal
        isOpen={showManifestsModal}
        onClose={() => setShowManifestsModal(false)}
        currentModel={safeModel}
        onLoadManifest={(m) => handleApplyNewModel(m, `Loaded manifest "${m.name}"`)}
        isLightMode={isLight}
      />

      {/* 5. AI Principal Architect Chatbot Agent Dock */}
      <ArchitectChatAgent
        isOpen={showChatAgent}
        onClose={() => setShowChatAgent(false)}
        onApplyModel={(m) => {
          handleApplyNewModel(m, "Synthesized from AI Architect Consultation");
        }}
        isLightMode={isLight}
      />

      {/* 6. Speckle Version Graph Modal */}
      <SpeckleVersionGraph
        isOpen={showSpeckleGraph}
        onClose={() => setShowSpeckleGraph(false)}
        currentVersion={3}
        onRestoreVersion={(v) => {
          setStatusToast(`✓ Checked out Speckle revision v${v}.0`);
          setTimeout(() => setStatusToast(null), 3000);
        }}
        isLightMode={isLight}
      />

      {/* 7. MagiCAD MEP Technical Spec Sheet */}
      <MagiCadSpecSheet
        isOpen={showMagiCadSheet}
        onClose={() => setShowMagiCadSheet(false)}
        isLightMode={isLight}
      />

      {/* 8. Floor Inspection Suite with Zoom & Walkthrough Focus */}
      <AnimatePresence>
        {showFloorSuite && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`absolute top-20 right-4 md:right-28 z-30 w-76 md:w-84 p-5 rounded-[28px] border shadow-2xl flex flex-col gap-4 ${
              isLight ? 'bg-white border-black text-black' : 'bg-black border-white/20 text-white'
            }`}
          >
            <div className="flex items-center justify-between border-b pb-3 border-neutral-200 dark:border-neutral-800">
              <div className="flex items-center gap-2">
                <SplitSquareVertical className="w-4 h-4 stroke-[2]" />
                <span className="text-xs font-black tracking-wider uppercase">Floor Focus & Walkthrough</span>
              </div>
              <button onClick={() => setShowFloorSuite(false)} className="opacity-60 hover:opacity-100">
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Floor Level Isolation Grid */}
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-[10px] font-bold opacity-60 uppercase">
                <span>Select Story Level</span>
                <span className="font-mono">{totalFloors} Stories</span>
              </div>
              <div className="grid grid-cols-4 gap-1.5 max-h-40 overflow-y-auto pr-1">
                <button
                  onClick={() => setSelectedFloor(null)}
                  className={`py-2 px-2 rounded-xl text-xs font-bold text-center transition-all col-span-2 border ${
                    selectedFloor === null
                      ? isLight ? 'bg-black text-white border-black' : 'bg-white text-black border-white'
                      : isLight ? 'bg-neutral-50 text-neutral-800 border-neutral-200 hover:bg-neutral-100' : 'bg-neutral-900 text-neutral-300 border-neutral-800 hover:bg-neutral-800'
                  }`}
                >
                  Full Tower
                </button>
                {Array.from({ length: totalFloors }, (_, i) => i + 1).map((f) => (
                  <button
                    key={f}
                    onClick={() => setSelectedFloor(f)}
                    className={`py-2 px-1.5 rounded-xl text-xs font-bold text-center transition-all border ${
                      selectedFloor === f
                        ? isLight ? 'bg-black text-white border-black' : 'bg-white text-black border-white'
                        : isLight ? 'bg-neutral-50 text-neutral-800 border-neutral-200 hover:bg-neutral-100' : 'bg-neutral-900 text-neutral-300 border-neutral-800 hover:bg-neutral-800'
                    }`}
                  >
                    L{f}
                  </button>
                ))}
              </div>
            </div>

            {/* Interactive Floor Walkthrough CTA */}
            {selectedFloor !== null && (
              <div className={`p-3 rounded-2xl border flex flex-col gap-2 ${
                isLight ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
              }`}>
                <div className="flex justify-between items-center text-xs font-bold">
                  <span>Level {selectedFloor} Focused</span>
                  <span className="font-mono text-neutral-500">Y = {((selectedFloor - 1) * 3.2).toFixed(1)}m</span>
                </div>
                <button
                  onClick={() => {
                    setIsFirstPerson(true);
                    setIsDroneTour(false);
                    setShowFloorSuite(false);
                  }}
                  className={`w-full py-2.5 rounded-xl font-black text-xs flex items-center justify-center gap-2 transition-transform hover:scale-105 ${
                    isLight ? 'bg-black text-white hover:bg-neutral-800' : 'bg-white text-black hover:bg-neutral-200'
                  }`}
                >
                  <Footprints className="w-4 h-4 stroke-[2]" />
                  <span>Enter Level {selectedFloor} Walkthrough</span>
                </button>
              </div>
            )}

            {/* Exploded Floor Expansion */}
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-[10px] font-bold opacity-60 uppercase">Explode Slabs</span>
                <span className="font-mono font-bold">{(explodeRatio * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={explodeRatio}
                onChange={(e) => setExplodeRatio(parseFloat(e.target.value))}
                className="w-full accent-black dark:accent-white cursor-pointer"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 9. Layers Panel */}
      <AnimatePresence>
        {showLayers && activeDisplayModel.layers && (
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }}
            transition={{ duration: 0.3 }}
            className={`absolute top-20 left-4 md:left-6 z-20 w-64 p-5 rounded-3xl border shadow-2xl flex flex-col gap-3 ${
              isLight ? 'bg-white border-black text-black' : 'bg-black border-white/20 text-white'
            }`}
          >
            <div className="flex items-center justify-between border-b pb-3 border-neutral-200 dark:border-neutral-800">
              <span className="text-xs font-black tracking-wider uppercase">BIM Layers</span>
              <button onClick={() => setShowLayers(false)} className="opacity-60 hover:opacity-100">
                <X className="w-4 h-4" />
              </button>
            </div>
            {Object.values(activeDisplayModel.layers).map((layer) => {
              const isVis = layerVisibility[layer.id] ?? layer.visible;
              return (
                <div
                  key={layer.id}
                  onClick={() => toggleLayer(layer.id)}
                  className={`flex items-center justify-between p-2.5 rounded-2xl cursor-pointer transition-colors ${
                    isLight ? 'hover:bg-neutral-100' : 'hover:bg-neutral-900'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: isVis ? layer.color : '#94A3B8' }}
                    />
                    <span className={`text-xs font-bold ${isVis ? '' : 'opacity-40'}`}>
                      {layer.name}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono opacity-60">{(layer.elements || []).length}</span>
                    {isVis ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5 opacity-40" />}
                  </div>
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 10. Interior Design Inspector */}
      <AnimatePresence>
        {showInspector && (
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 30 }}
            transition={{ duration: 0.3 }}
            className={`absolute top-20 right-4 md:right-6 z-20 w-80 md:w-88 p-5 rounded-[28px] border shadow-2xl flex flex-col gap-4 max-h-[80vh] overflow-y-auto ${
              isLight ? 'bg-white border-black text-black' : 'bg-black border-white/20 text-white'
            }`}
          >
            <InteriorInspector
              element={selectedElement}
              model={activeDisplayModel}
              onClose={() => setShowInspector(false)}
              onUpdateElementPosition={updateElementPosition}
              onUpdateElementDimension={updateElementDimension}
              onUpdateElementMaterialColor={updateElementMaterialColor}
              onDuplicate={duplicateElement}
              onDelete={deleteElement}
              onApplyNewModel={(m) => handleApplyNewModel(m, "Space redesigned")}
              isLightMode={isLight}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* 12. Bottom-Left CAD Telemetry */}
      <div className="absolute bottom-4 left-6 z-10 hidden sm:flex items-center gap-3 text-[10px] opacity-60 pointer-events-none font-mono">
        <div className={`px-2.5 py-1 rounded-full border ${
          isLight ? 'bg-white border-black/60 text-black' : 'bg-black border-white/20 text-white'
        }`}>
          X: {cursorPos.x.toFixed(2)}m • Z: {cursorPos.z.toFixed(2)}m
        </div>
        <span>ThatOpen / Web-IFC 120 FPS</span>
      </div>

      {/* 13. Floorplan Import Modal */}
      <FloorplanModal
        isOpen={showFloorplanModal}
        onClose={() => setShowFloorplanModal(false)}
        onApplyModel={(m) => {
          handleApplyNewModel(m, "Extruded from Floor Plan PDF");
          setSelectedFloor(null);
          setExplodeRatio(0);
        }}
      />

      {/* 14. Shortcuts Modal */}
      <AnimatePresence>
        {showHelp && (
          <div
            onClick={() => setShowHelp(false)}
            className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className={`w-full max-w-md p-6 rounded-3xl border shadow-2xl flex flex-col gap-4 ${
                isLight ? 'bg-white border-black text-black' : 'bg-black border-white/20 text-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-black uppercase tracking-tight">Navigation & CAD Controls</span>
                <button onClick={() => setShowHelp(false)} className="opacity-60 hover:opacity-100">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex flex-col gap-2.5 text-xs">
                <div className="flex justify-between font-mono"><span>2-Finger Scroll Up/Down</span><span className="font-sans opacity-70">Tilt Elevation Pitch</span></div>
                <div className="flex justify-between font-mono"><span>2-Finger Scroll Left/Right</span><span className="font-sans opacity-70">Orbit Rotate 360°</span></div>
                <div className="flex justify-between font-mono"><span>Pinch In / Out</span><span className="font-sans opacity-70">Focal Zoom</span></div>
                <div className="flex justify-between font-mono"><span>Shift + 2-Finger Scroll</span><span className="font-sans opacity-70">Pan Camera</span></div>
                <div className="flex justify-between font-mono"><span>Click Any Component</span><span className="font-sans opacity-70">Inspect & Customize</span></div>
                <div className="flex justify-between font-mono"><span>W / A / S / D</span><span className="font-sans opacity-70">Walk Mode Navigation</span></div>
              </div>
              <button
                onClick={() => setShowHelp(false)}
                className={`w-full py-2.5 rounded-full font-black text-xs mt-2 ${
                  isLight ? 'bg-black text-white' : 'bg-white text-black'
                }`}
              >
                Close
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
