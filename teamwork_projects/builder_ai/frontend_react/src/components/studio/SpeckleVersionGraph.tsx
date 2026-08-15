import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, GitCommit, Clock, CheckCircle2, RotateCcw, X, ArrowRight, Layers, User } from 'lucide-react';

interface SpeckleVersion {
  version: number;
  commit_id: string;
  author: string;
  timestamp: string;
  message: string;
  element_count: number;
  lod: string;
}

interface SpeckleVersionGraphProps {
  isOpen: boolean;
  onClose: () => void;
  currentVersion: number;
  onRestoreVersion: (versionNum: number) => void;
  isLightMode?: boolean;
}

export const SpeckleVersionGraph: React.FC<SpeckleVersionGraphProps> = ({
  isOpen,
  onClose,
  currentVersion,
  onRestoreVersion,
  isLightMode = false,
}) => {
  const [selectedCommit, setSelectedCommit] = useState<number>(currentVersion || 3);

  const versions: SpeckleVersion[] = [
    {
      version: 1,
      commit_id: "c_init_89a1",
      author: "Principal Architect AI",
      timestamp: "Initial Synthesis",
      message: "v1.0: Volumetric massing & structural grid layout",
      element_count: 28,
      lod: "LOD 200 (Massing)",
    },
    {
      version: 2,
      commit_id: "c_mep_90b2",
      author: "MagiCAD MEP Engine",
      timestamp: "Engineering Pass",
      message: "v2.0: Routed 110mm wet stack, electrical busbars & risers",
      element_count: 56,
      lod: "LOD 350 (MEP Systems)",
    },
    {
      version: 3,
      commit_id: "c_arch_91c3",
      author: "OpenBIM Studio",
      timestamp: "Active Revision",
      message: "v3.0: 2BHK/3BHK units, interior styling, elevator cores & PBR materials",
      element_count: 241,
      lod: "LOD 400 (High Detail)",
    },
  ];

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: -20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -20 }}
      className={`absolute top-20 right-4 md:right-28 z-30 w-88 md:w-[420px] p-6 rounded-[32px] border shadow-2xl flex flex-col gap-4 max-h-[82vh] overflow-y-auto ${
        isLightMode ? 'bg-white/95 border-slate-200 text-slate-900' : 'glass-card border-[#38BDF8]/40 text-white'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-3 border-white/10">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-[#38BDF8]/20 text-[#38BDF8]">
            <GitBranch className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-black tracking-wider">SPECKLE 3D VERSION GRAPH</div>
            <div className="text-[10px] opacity-60">Object-level graph versioning & commit diffs</div>
          </div>
        </div>
        <button onClick={onClose} className="opacity-60 hover:opacity-100 p-1">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Timeline Commit List */}
      <div className="flex flex-col gap-3 relative pl-4 border-l-2 border-[#38BDF8]/30">
        {versions.map((ver) => {
          const isSelected = selectedCommit === ver.version;
          return (
            <div
              key={ver.commit_id}
              onClick={() => setSelectedCommit(ver.version)}
              className={`p-3.5 rounded-2xl border cursor-pointer transition-all flex flex-col gap-2 relative ${
                isSelected
                  ? 'border-[#38BDF8] bg-[#38BDF8]/10 shadow-lg'
                  : isLightMode
                  ? 'bg-slate-50 border-slate-200 hover:border-slate-300'
                  : 'bg-black/40 border-white/5 hover:border-white/20'
              }`}
            >
              {/* Timeline Indicator Dot */}
              <div
                className={`absolute -left-[23px] top-5 w-3 h-3 rounded-full border-2 transition-all ${
                  isSelected
                    ? 'bg-[#38BDF8] border-white shadow-[0_0_10px_#38BDF8]'
                    : isLightMode ? 'bg-slate-300 border-white' : 'bg-[#0E1015] border-[#38BDF8]/60'
                }`}
              />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] font-bold text-[#38BDF8]">{ver.commit_id}</span>
                  <span className="text-[10px] opacity-60">{ver.timestamp}</span>
                </div>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-[#38BDF8]/15 text-[#38BDF8] font-bold">
                  {ver.lod}
                </span>
              </div>

              <p className={`text-xs font-bold ${isLightMode ? 'text-slate-800' : 'text-white'}`}>{ver.message}</p>

              <div className="flex items-center justify-between text-[10px] opacity-70 pt-1 border-t border-white/5">
                <div className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  <span>{ver.author}</span>
                </div>
                <span>{ver.element_count} 3D objects</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Footer */}
      <div className="flex items-center gap-2 pt-2 border-t border-white/10">
        <button
          onClick={() => {
            onRestoreVersion(selectedCommit);
            onClose();
          }}
          className="flex-1 py-3 rounded-full bg-[#38BDF8] text-black font-extrabold text-xs flex items-center justify-center gap-2 shadow-lg hover:scale-105 transition-all"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Checkout Commit (v{selectedCommit}.0)</span>
        </button>
      </div>
    </motion.div>
  );
};
