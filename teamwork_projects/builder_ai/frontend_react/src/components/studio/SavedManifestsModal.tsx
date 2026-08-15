import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FolderGit2, Plus, Download, Trash2, Check, Clock, Eye, Layers, Building2, X, Sparkles, FileCode, Tag } from 'lucide-react';
import { BuildingModel } from '../../types/model';
import { defaultVillaModel, sanitizeBuildingModel } from '../../services/api';
import { cityDistrictModel, societyCampusModel } from '../../services/lodHierarchy';

export interface SavedManifest {
  id: string;
  name: string;
  description: string;
  createdAt: string;
  elementCount: number;
  floorsCount: number;
  tags: string[];
  modelData: BuildingModel;
}

const STORAGE_KEY = 'builder_ai_saved_manifests_v1';

// Seed Initial Saved Manifests
const INITIAL_MANIFESTS: SavedManifest[] = [
  {
    id: 'manifest_villa_aurora',
    name: 'Vinewood OpenBIM Luxury Villa',
    description: '2-story luxury residence with Calacatta island, master suite, infinity pool & PBR shaders.',
    createdAt: 'Today, 06:30 PM',
    elementCount: 73,
    floorsCount: 2,
    tags: ['Villa', 'Furnished', 'LOD 400'],
    modelData: defaultVillaModel,
  },
  {
    id: 'manifest_12story_tower',
    name: '12-Story Residential Tower (2BHK & 3BHK)',
    description: '12 floors, 2 apartments per floor (Unit 1: 2BHK West Wing, Unit 2: 3BHK East Wing) with central core.',
    createdAt: 'Today, 09:15 PM',
    elementCount: 241,
    floorsCount: 12,
    tags: ['High-Rise', '2BHK/3BHK', '12 Floors', 'LOD 350'],
    modelData: defaultVillaModel, // Populated dynamically or when loaded
  },
  {
    id: 'manifest_society_campus',
    name: 'Vinewood Hills Society Masterplan',
    description: 'Multi-building development: Tower A, Commercial Wing, Villa, and Central Park.',
    createdAt: 'Yesterday, 04:00 PM',
    elementCount: 14,
    floorsCount: 14,
    tags: ['Masterplan', 'Cesium 3D Tiles', 'LOD 200'],
    modelData: societyCampusModel,
  },
];

interface SavedManifestsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentModel: BuildingModel;
  onLoadManifest: (model: BuildingModel) => void;
  isLightMode?: boolean;
}

export const SavedManifestsModal: React.FC<SavedManifestsModalProps> = ({
  isOpen,
  onClose,
  currentModel,
  onLoadManifest,
  isLightMode = false,
}) => {
  const [manifests, setManifests] = useState<SavedManifest[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return INITIAL_MANIFESTS;
  });

  const [searchQuery, setSearchQuery] = useState('');
  const [saveTitle, setSaveTitle] = useState('');
  const [saveTag, setSaveTag] = useState('');
  const [showSaveForm, setShowSaveForm] = useState(false);

  // Sync to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(manifests));
    } catch (e) {}
  }, [manifests]);

  if (!isOpen) return null;

  const totalElements = Object.values(currentModel.layers || {}).reduce(
    (acc, l) => acc + (l.elements || []).length,
    0
  );

  const handleSaveCurrentModel = () => {
    if (!saveTitle.trim()) return;

    const newManifest: SavedManifest = {
      id: `manifest_${Date.now()}`,
      name: saveTitle.trim(),
      description: currentModel.description || `Manifested BIM model with ${totalElements} structural & MEP elements.`,
      createdAt: 'Just now',
      elementCount: totalElements,
      floorsCount: Math.max(1, Math.round(totalElements / 18)),
      tags: saveTag ? saveTag.split(',').map((t) => t.trim()) : ['Custom BIM', 'LOD 350'],
      modelData: JSON.parse(JSON.stringify(currentModel)),
    };

    setManifests([newManifest, ...manifests]);
    setSaveTitle('');
    setSaveTag('');
    setShowSaveForm(false);
  };

  const handleDeleteManifest = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setManifests(manifests.filter((m) => m.id !== id));
  };

  const handleExportJSON = (manifest: SavedManifest, e: React.MouseEvent) => {
    e.stopPropagation();
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(manifest.modelData, null, 2));
    const a = document.createElement('a');
    a.setAttribute("href", dataStr);
    a.setAttribute("download", `${manifest.name.replace(/\s+/g, '_')}_manifest.json`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  const filteredManifests = manifests.filter(
    (m) =>
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 15 }}
        onClick={(e) => e.stopPropagation()}
        className={`w-full max-w-3xl rounded-[32px] p-6 md:p-8 flex flex-col gap-6 shadow-2xl border max-h-[88vh] overflow-hidden ${
          isLightMode
            ? 'bg-white/95 border-black/10 text-slate-900'
            : 'bg-[#0E1015]/95 border-white/10 text-white'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-4 border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-[#D4FF32]/20 flex items-center justify-center text-[#D4FF32]">
              <FolderGit2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-black tracking-wide flex items-center gap-2">
                <span>MANIFEST LIBRARY & SAVED MODELS</span>
                <span className="px-2 py-0.5 rounded-full bg-[#D4FF32]/20 text-[#D4FF32] text-[10px] font-mono">
                  {manifests.length} SAVED
                </span>
              </h2>
              <p className={`text-xs ${isLightMode ? 'text-slate-500' : 'text-[#8E8F9C]'}`}>
                Persistent repository of previously manifested and synthesized 3D OpenBIM buildings
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className={`p-2 rounded-full hover:scale-110 transition-transform ${
              isLightMode ? 'hover:bg-slate-100 text-slate-600' : 'hover:bg-white/10 text-[#8E8F9C]'
            }`}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Action Bar & Search */}
        <div className="flex flex-col sm:flex-row items-center gap-3 justify-between">
          <input
            type="text"
            placeholder="Search saved models or tags (e.g. 12-Story, Villa, Masterplan)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`w-full sm:w-80 px-4 py-2.5 rounded-full text-xs outline-none border transition-all ${
              isLightMode
                ? 'bg-slate-100 border-slate-200 text-slate-900 focus:border-[#D4FF32]'
                : 'bg-black/50 border-white/10 text-white focus:border-[#D4FF32]'
            }`}
          />

          <button
            onClick={() => setShowSaveForm(!showSaveForm)}
            className="w-full sm:w-auto px-4 py-2.5 rounded-full bg-[#D4FF32] text-black font-extrabold text-xs flex items-center justify-center gap-2 shadow-lg hover:scale-105 transition-transform shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Save Current Viewport Model</span>
          </button>
        </div>

        {/* Save Current Model Form */}
        <AnimatePresence>
          {showSaveForm && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className={`p-4 rounded-2xl border flex flex-col gap-3 ${
                isLightMode ? 'bg-slate-50 border-slate-200' : 'bg-black/40 border-[#D4FF32]/30'
              }`}
            >
              <div className="text-xs font-black text-[#D4FF32]">SAVE MANIFEST SNAPSHOT</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Manifest Name (e.g. 12-Story 2BHK/3BHK Tower)..."
                  value={saveTitle}
                  onChange={(e) => setSaveTitle(e.target.value)}
                  className={`px-3 py-2 rounded-xl text-xs outline-none border ${
                    isLightMode ? 'bg-white border-slate-300' : 'bg-black/60 border-white/10'
                  }`}
                />
                <input
                  type="text"
                  placeholder="Tags comma-separated (e.g. High-Rise, 12-Story, Residential)..."
                  value={saveTag}
                  onChange={(e) => setSaveTag(e.target.value)}
                  className={`px-3 py-2 rounded-xl text-xs outline-none border ${
                    isLightMode ? 'bg-white border-slate-300' : 'bg-black/60 border-white/10'
                  }`}
                />
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setShowSaveForm(false)}
                  className="px-3 py-1.5 rounded-xl text-xs text-[#8E8F9C] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveCurrentModel}
                  disabled={!saveTitle.trim()}
                  className="px-4 py-1.5 rounded-xl bg-[#D4FF32] text-black font-extrabold text-xs disabled:opacity-40"
                >
                  Save Manifest ({totalElements} entities)
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Manifests Grid List */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-4 pr-1">
          {filteredManifests.map((item) => (
            <div
              key={item.id}
              onClick={() => {
                onLoadManifest(sanitizeBuildingModel(item.modelData));
                onClose();
              }}
              className={`p-5 rounded-3xl border transition-all cursor-pointer flex flex-col justify-between gap-3 group relative hover:scale-[1.01] ${
                isLightMode
                  ? 'bg-slate-50 border-slate-200 hover:border-slate-400 hover:shadow-xl'
                  : 'bg-black/40 border-white/10 hover:border-[#D4FF32]/60 hover:shadow-[0_0_25px_rgba(212,255,50,0.15)]'
              }`}
            >
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-[#D4FF32]" />
                    <span className="text-xs font-black leading-tight tracking-wide">{item.name}</span>
                  </div>
                  <span className="text-[10px] font-mono text-[#8E8F9C] flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{item.createdAt}</span>
                  </span>
                </div>

                <p className={`text-[11px] line-clamp-2 leading-relaxed ${isLightMode ? 'text-slate-600' : 'text-[#8E8F9C]'}`}>
                  {item.description}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {item.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className={`text-[9px] font-mono px-2 py-0.5 rounded-full ${
                        isLightMode
                          ? 'bg-slate-200 text-slate-700'
                          : 'bg-white/5 text-[#8E8F9C] border border-white/5'
                      }`}
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>

              {/* Card Footer: Metadata & Actions */}
              <div className="flex items-center justify-between pt-3 border-t border-white/5 text-[10px]">
                <div className="flex items-center gap-3 text-[#8E8F9C] font-mono">
                  <span>{item.elementCount} elements</span>
                  <span>•</span>
                  <span>{item.floorsCount} floors</span>
                </div>

                <div className="flex items-center gap-1.5 opacity-80 group-hover:opacity-100">
                  <button
                    onClick={(e) => handleExportJSON(item, e)}
                    className="p-1.5 rounded-lg hover:bg-white/10 text-[#8E8F9C] hover:text-[#D4FF32] transition-colors"
                    title="Export JSON Manifest"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={(e) => handleDeleteManifest(item.id, e)}
                    className="p-1.5 rounded-lg hover:bg-red-500/20 text-[#8E8F9C] hover:text-red-400 transition-colors"
                    title="Delete Manifest"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <span className="px-3 py-1 rounded-full bg-[#D4FF32] text-black font-extrabold text-[10px] ml-1">
                    Load Model ➜
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
};
