import React from 'react';
import { motion } from 'framer-motion';
import { Globe, LayoutGrid, Building2, Layers, Home, Cpu } from 'lucide-react';
import { LodLevel, LOD_HIERARCHY } from '../../services/lodHierarchy';

interface SpatialHierarchyNavProps {
  currentLod: LodLevel;
  onSelectLod: (lod: LodLevel) => void;
  availableScales?: string[];
  isLightMode?: boolean;
}

const getLodIcon = (id: LodLevel) => {
  switch (id) {
    case 'city':
      return <Globe className="w-3.5 h-3.5" strokeWidth={1.5} />;
    case 'society':
      return <LayoutGrid className="w-3.5 h-3.5" strokeWidth={1.5} />;
    case 'building':
      return <Building2 className="w-3.5 h-3.5" strokeWidth={1.5} />;
    case 'storey':
      return <Layers className="w-3.5 h-3.5" strokeWidth={1.5} />;
    case 'apartment':
      return <Home className="w-3.5 h-3.5" strokeWidth={1.5} />;
    case 'mep':
      return <Cpu className="w-3.5 h-3.5" strokeWidth={1.5} />;
    default:
      return <Building2 className="w-3.5 h-3.5" strokeWidth={1.5} />;
  }
};

export const SpatialHierarchyNav: React.FC<SpatialHierarchyNavProps> = ({
  currentLod,
  onSelectLod,
  availableScales,
  isLightMode = false,
}) => {
  const visibleNodes = LOD_HIERARCHY.filter((node) => {
    if (!availableScales || availableScales.length === 0) {
      return node.id === 'building' || node.id === 'storey' || node.id === 'apartment' || node.id === 'mep';
    }
    return availableScales.includes(node.id) || (availableScales.includes('floor') && (node.id === 'storey' || node.id === 'apartment'));
  });

  return (
    <nav className={`flex items-center gap-1 p-1 rounded-full border transition-all duration-200 ${
      isLightMode
        ? 'bg-white border-black/80 shadow-sm'
        : 'bg-black border-white/20 shadow-xl'
    }`}>
      {visibleNodes.map((node) => {
        const isActive = currentLod === node.id;
        return (
          <button
            key={node.id}
            onClick={() => onSelectLod(node.id)}
            className={`relative px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-tight transition-all flex items-center gap-2 cursor-pointer ${
              isActive
                ? isLightMode
                  ? 'bg-black text-white shadow-sm font-bold'
                  : 'bg-white text-black shadow-sm font-bold'
                : isLightMode
                ? 'text-neutral-600 hover:text-black hover:bg-neutral-100'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-900'
            }`}
            title={`${node.label} (${node.sublabel})`}
          >
            <span className="relative z-10">{getLodIcon(node.id)}</span>
            <span className="relative z-10 hidden sm:inline text-[11px] uppercase tracking-wider">{node.label.split(' ')[0]}</span>
          </button>
        );
      })}
    </nav>
  );
};
