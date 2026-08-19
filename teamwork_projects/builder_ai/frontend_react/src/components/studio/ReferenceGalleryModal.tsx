import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Image, Sparkles, Layers, Box, Cpu, Check, Compass, Eye,
  Download, ExternalLink, Filter, Search, ArrowRight, Grid
} from 'lucide-react';

export interface ReferenceItem {
  id: string;
  title: string;
  category: 'commercial' | 'residential' | 'cad_mep' | 'interiors';
  typology: string;
  description: string;
  imageUrl: string;
  cadSpecs: {
    dimensions: string;
    structuralGrid: string;
    primaryMaterials: string[];
    mepStandard: string;
    acousticRating: string;
  };
  palette: {
    name: string;
    walls: string;
    flooring: string;
    accent: string;
    furniture: string;
  };
  promptHint: string;
}

export const ARCHITECTURAL_REFERENCES: ReferenceItem[] = [
  {
    id: 'ref_com_tower',
    title: 'Grade-A Commercial Tower Floorplate',
    category: 'commercial',
    typology: '12-Storey Commercial Office Tower',
    description: 'Central dual elevator and fire stair core with 4x collaborative workstation pods, 14-person boardroom, and acoustic perimeter glazing.',
    imageUrl: 'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1200&q=80',
    cadSpecs: {
      dimensions: '36.0m x 24.0m x 3.8m floor-to-floor',
      structuralGrid: '8.0m x 8.0m RC Column Matrix with Shear Core',
      primaryMaterials: ['Low-E Solar Glazing', 'Fluted Acoustic Walnut', 'Anodized Dark Mullions'],
      mepStandard: 'VAV Variable Air Volume + 415V Busbar Riser',
      acousticRating: 'STC 52 / NRC 0.85',
    },
    palette: {
      name: 'Corporate Modern',
      walls: '#F1F5F9',
      flooring: '#E2E8F0',
      accent: '#0F172A',
      furniture: '#334155',
    },
    promptHint: '12 story commercial office tower with central elevator core, open workstations, executive boardroom and MEP risers',
  },
  {
    id: 'ref_boardroom',
    title: 'Executive 14-Person Boardroom Suite',
    category: 'commercial',
    typology: 'Corporate Conference & AV Hub',
    description: 'Solid chamfered walnut racetrack table with integrated pop-up AV connectivity, 14 ergonomic executive swivel chairs, and acoustic timber wall panels.',
    imageUrl: 'https://images.unsplash.com/photo-1517502884422-41eaead166d4?auto=format&fit=crop&w=1200&q=80',
    cadSpecs: {
      dimensions: '8.4m x 5.6m (47.0 sqm)',
      structuralGrid: 'Column-free clear span with double acoustic glazed partition',
      primaryMaterials: ['American Black Walnut', 'Brushed Bronze Hardware', 'Full-Grain Leather'],
      mepStandard: 'Dedicated 4-Pipe Fan Coil Unit + 500 Lux Dimmable Lighting',
      acousticRating: 'STC 55 Sound Transmission Class',
    },
    palette: {
      name: 'Executive Walnut',
      walls: '#FAF7F2',
      flooring: '#D4A373',
      accent: '#78350F',
      furniture: '#1E293B',
    },
    promptHint: 'Executive boardroom with walnut racetrack conference table, 14 swivel chairs, 85 inch display and acoustic timber paneling',
  },
  {
    id: 'ref_workstations',
    title: 'Open Collaborative Workstation Cluster',
    category: 'interiors',
    typology: '6-Person Desking & Focus Pods',
    description: 'Powder-coated steel O-frame desking with acoustic fabric privacy screens, dual 4K monitor arms, and private acoustic phone booths.',
    imageUrl: 'https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1200&q=80',
    cadSpecs: {
      dimensions: '3.6m x 1.4m per pod cluster',
      structuralGrid: 'Underfloor modular cable grommet & busway grid',
      primaryMaterials: ['Powder-Coated Steel', 'Acoustic PET Felt', 'High-Pressure Laminate'],
      mepStandard: 'Under-desk cable management + 4000K LED troffer array',
      acousticRating: 'NRC 0.90 Sound Absorption',
    },
    palette: {
      name: 'High-Tech Minimal',
      walls: '#FFFFFF',
      flooring: '#CBD5E1',
      accent: '#3B82F6',
      furniture: '#0F172A',
    },
    promptHint: 'Open office workstations with ergonomic mesh chairs, dual monitors, acoustic dividers and focus phone booths',
  },
  {
    id: 'ref_villa_luxury',
    title: '2-Storey Contemporary Luxury Villa',
    category: 'residential',
    typology: 'Modern Residential Villa',
    description: 'Double-height living pavilion, waterfall Calacatta kitchen island, master sleeping suite with terrace, and rooftop infinity pool.',
    imageUrl: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80',
    cadSpecs: {
      dimensions: '22.0m x 16.0m x 7.2m total height',
      structuralGrid: '6.0m x 6.0m Post-Tensioned Concrete Slab with Cantilever Deck',
      primaryMaterials: ['Calacatta Caldia Marble', 'Fluted Oak', 'Thermally Broken Black Aluminum'],
      mepStandard: 'Concealed VRF Multi-Split HVAC + Rooftop Solar PV',
      acousticRating: 'STC 48 / Residential Class A',
    },
    palette: {
      name: 'Contemporary Modern',
      walls: '#E2E8F0',
      flooring: '#C9935E',
      accent: '#0F172A',
      furniture: '#334155',
    },
    promptHint: '2-storey luxury villa with double-height living room, quartz kitchen island, master bedroom suite and rooftop pool',
  },
  {
    id: 'ref_penthouse',
    title: '3BHK Urban Master Suite Penthouse',
    category: 'residential',
    typology: 'High-Rise Residential Suite',
    description: 'Panoramic glass balustrade perimeter, master suite platform bed with acoustic fluted headboard, walk-in closet, and freestanding soaking tub.',
    imageUrl: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=80',
    cadSpecs: {
      dimensions: '18.0m x 12.0m (216 sqm floor area)',
      structuralGrid: 'Flat plate concrete slab with acoustic underlayment',
      primaryMaterials: ['Honed Engineered Oak', 'Bouclé Fabric', 'Brushed Bronze'],
      mepStandard: 'Ducted ceiling fresh air ERV + Hydrozone Plumbing Battery',
      acousticRating: 'STC 50 / IIC 54 Impact Insulation',
    },
    palette: {
      name: 'Japandi Warm',
      walls: '#FAF7F2',
      flooring: '#D4A373',
      accent: '#78350F',
      furniture: '#D6C7B2',
    },
    promptHint: '3BHK luxury penthouse with master platform bed, linen upholstery, soaking tub and oak hardwood flooring',
  },
  {
    id: 'ref_cad_mep',
    title: 'BIM 6-Tier Spatial & MEP Riser Network',
    category: 'cad_mep',
    typology: 'OpenBIM Structural & MEP Engineering',
    description: 'Axonometric BIM coordination: Dual DN150 soil/waste plumbing risers, 415V electrical floor panels, busbar conduits, and roof HVAC chillers.',
    imageUrl: 'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=1200&q=80',
    cadSpecs: {
      dimensions: 'Full building height MEP riser shafts',
      structuralGrid: 'Dedicated 2.4m x 1.8m MEP vertical riser cores',
      primaryMaterials: ['Galvanized Sheet Steel (Ductwork)', 'PEX-a / Copper (Supply)', 'Cast Iron (Soil/Waste)'],
      mepStandard: 'ASHRAE 90.1 & IEC 61439 compliant 415V 3-phase',
      acousticRating: 'Vibration isolated mounts < 35 dBA',
    },
    palette: {
      name: 'MEP Engineering',
      walls: '#1E293B',
      flooring: '#334155',
      accent: '#F59E0B',
      furniture: '#06B6D4',
    },
    promptHint: 'Commercial building with 6 semantic BIM layers, 415V electrical distribution panels, plumbing soil risers and rooftop chillers',
  }
];

interface ReferenceGalleryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyPrompt: (promptText: string) => void;
  onApplyPalette?: (palette: ReferenceItem['palette']) => void;
}

export const ReferenceGalleryModal: React.FC<ReferenceGalleryModalProps> = ({
  isOpen,
  onClose,
  onApplyPrompt,
  onApplyPalette,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<'all' | 'commercial' | 'residential' | 'cad_mep' | 'interiors'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRef, setSelectedRef] = useState<ReferenceItem | null>(ARCHITECTURAL_REFERENCES[0]);

  if (!isOpen) return null;

  const filteredReferences = ARCHITECTURAL_REFERENCES.filter((ref) => {
    const matchesCat = selectedCategory === 'all' || ref.category === selectedCategory;
    const matchesSearch = searchQuery === '' ||
      ref.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ref.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ref.typology.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 sm:p-6">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2 }}
          className="relative w-full max-w-6xl h-[88vh] bg-[#0F1117] border border-[#2B2F3D] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-[#2B2F3D] bg-[#161922]">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#D4FF32]/10 border border-[#D4FF32]/30 flex items-center justify-center text-[#D4FF32]">
                <Image className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  Architectural CAD & Typology Reference Gallery
                  <span className="px-2 py-0.5 text-[10px] font-semibold bg-[#D4FF32] text-black rounded-full uppercase tracking-wider">
                    BIM Sourced
                  </span>
                </h2>
                <p className="text-xs text-neutral-400">
                  Inspect high-fidelity CAD layouts, material moodboards, and structural details to apply directly to your model
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-[#1E222D] hover:bg-[#2B2F3D] text-neutral-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Search & Category Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 border-b border-[#2B2F3D] bg-[#12151D]">
            {/* Category Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto py-1">
              {[
                { id: 'all', label: 'All References' },
                { id: 'commercial', label: 'Commercial Offices' },
                { id: 'residential', label: 'Residential Villas' },
                { id: 'interiors', label: 'Workstations & Boardrooms' },
                { id: 'cad_mep', label: 'CAD & MEP Engineering' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSelectedCategory(tab.id as any)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                    selectedCategory === tab.id
                      ? 'bg-[#D4FF32] text-black shadow-lg shadow-[#D4FF32]/20 font-bold'
                      : 'bg-[#1A1D27] text-neutral-400 hover:text-white hover:bg-[#242836]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative min-w-[240px]">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
              <input
                type="text"
                placeholder="Search CAD details, styles, MEP..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-[#1A1D27] border border-[#2B2F3D] rounded-lg text-white placeholder-neutral-500 focus:outline-none focus:border-[#D4FF32]"
              />
            </div>
          </div>

          {/* Main Content Body */}
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-0 overflow-hidden">
            {/* Left Grid: Reference Cards (7 cols) */}
            <div className="lg:col-span-7 p-6 overflow-y-auto border-r border-[#2B2F3D] space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {filteredReferences.map((item) => {
                  const isSelected = selectedRef?.id === item.id;
                  return (
                    <div
                      key={item.id}
                      onClick={() => setSelectedRef(item)}
                      className={`group relative rounded-xl border overflow-hidden cursor-pointer transition-all ${
                        isSelected
                          ? 'border-[#D4FF32] bg-[#1A1E29] ring-2 ring-[#D4FF32]/30 shadow-xl'
                          : 'border-[#2B2F3D] bg-[#141720] hover:border-neutral-500 hover:bg-[#1A1D27]'
                      }`}
                    >
                      {/* Image Thumbnail */}
                      <div className="relative h-40 w-full overflow-hidden bg-neutral-900">
                        <img
                          src={item.imageUrl}
                          alt={item.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                        <span className="absolute top-2 left-2 px-2 py-0.5 text-[10px] font-bold uppercase rounded-md bg-black/70 backdrop-blur-md text-[#D4FF32] border border-[#D4FF32]/30">
                          {item.category.replace('_', ' ')}
                        </span>
                        {isSelected && (
                          <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-[#D4FF32] text-black flex items-center justify-center shadow-lg">
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          </div>
                        )}
                      </div>

                      {/* Content */}
                      <div className="p-3.5 space-y-2">
                        <h3 className="text-sm font-bold text-white group-hover:text-[#D4FF32] transition-colors leading-tight">
                          {item.title}
                        </h3>
                        <p className="text-xs text-neutral-400 line-clamp-2 leading-relaxed">
                          {item.description}
                        </p>

                        {/* Palette Previews */}
                        <div className="flex items-center gap-1.5 pt-1">
                          <span className="text-[10px] text-neutral-500 font-mono">Colors:</span>
                          {[item.palette.walls, item.palette.flooring, item.palette.accent, item.palette.furniture].map((c, i) => (
                            <span
                              key={i}
                              className="w-3.5 h-3.5 rounded-full border border-black/40 shadow-sm"
                              style={{ backgroundColor: c }}
                              title={c}
                            />
                          ))}
                          <span className="text-[10px] text-neutral-400 font-medium ml-1">
                            {item.palette.name}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right Panel: Selected Reference CAD Inspector & Apply Actions (5 cols) */}
            {selectedRef && (
              <div className="lg:col-span-5 p-6 overflow-y-auto bg-[#12151D] flex flex-col justify-between space-y-6">
                <div className="space-y-5">
                  {/* Big Image Header */}
                  <div className="relative rounded-xl overflow-hidden border border-[#2B2F3D] h-52 bg-black shadow-lg">
                    <img
                      src={selectedRef.imageUrl}
                      alt={selectedRef.title}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/30 to-transparent" />
                    <div className="absolute bottom-3 left-3 right-3">
                      <span className="text-[10px] font-bold text-[#D4FF32] uppercase tracking-wider">
                        {selectedRef.typology}
                      </span>
                      <h3 className="text-base font-bold text-white">
                        {selectedRef.title}
                      </h3>
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-xs text-neutral-300 leading-relaxed bg-[#181C26] p-3 rounded-lg border border-[#2B2F3D]">
                    {selectedRef.description}
                  </p>

                  {/* CAD Specifications Matrix */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-[#D4FF32]" />
                      CAD & BIM Engineering Specifications
                    </h4>
                    <div className="space-y-1.5 text-xs bg-[#161922] p-3 rounded-xl border border-[#2B2F3D]">
                      <div className="flex justify-between py-1 border-b border-[#242836]">
                        <span className="text-neutral-400">Dimensions:</span>
                        <span className="text-neutral-200 font-mono font-semibold">{selectedRef.cadSpecs.dimensions}</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-[#242836]">
                        <span className="text-neutral-400">Structural Grid:</span>
                        <span className="text-neutral-200 font-semibold">{selectedRef.cadSpecs.structuralGrid}</span>
                      </div>
                      <div className="flex justify-between py-1 border-b border-[#242836]">
                        <span className="text-neutral-400">MEP Standard:</span>
                        <span className="text-[#38BDF8] font-mono font-semibold">{selectedRef.cadSpecs.mepStandard}</span>
                      </div>
                      <div className="flex justify-between py-1">
                        <span className="text-neutral-400">Acoustic Class:</span>
                        <span className="text-[#10B981] font-mono font-semibold">{selectedRef.cadSpecs.acousticRating}</span>
                      </div>
                    </div>
                  </div>

                  {/* Material Palette Swatches */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-[#D4FF32]" />
                      Architectural Palette: {selectedRef.palette.name}
                    </h4>
                    <div className="grid grid-cols-4 gap-2">
                      {[
                        { label: 'Walls', color: selectedRef.palette.walls },
                        { label: 'Flooring', color: selectedRef.palette.flooring },
                        { label: 'Accents', color: selectedRef.palette.accent },
                        { label: 'Furnishing', color: selectedRef.palette.furniture },
                      ].map((swatch, idx) => (
                        <div
                          key={idx}
                          className="bg-[#161922] border border-[#2B2F3D] rounded-lg p-2 flex flex-col items-center gap-1"
                        >
                          <div
                            className="w-full h-7 rounded border border-black/40 shadow-inner"
                            style={{ backgroundColor: swatch.color }}
                          />
                          <span className="text-[10px] text-neutral-400 font-medium">{swatch.label}</span>
                          <span className="text-[9px] text-neutral-500 font-mono">{swatch.color}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Bottom Actions: Apply to Live Model */}
                <div className="pt-4 border-t border-[#2B2F3D] space-y-2">
                  <button
                    onClick={() => {
                      onApplyPrompt(selectedRef.promptHint);
                      if (onApplyPalette) onApplyPalette(selectedRef.palette);
                      onClose();
                    }}
                    className="w-full py-3 px-4 rounded-xl bg-[#D4FF32] hover:bg-[#bceb2b] text-black font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-[#D4FF32]/25 transition-all transform active:scale-98"
                  >
                    <Sparkles className="w-4 h-4 fill-black" />
                    Apply Typology & Materials to 3D Model
                    <ArrowRight className="w-4 h-4" />
                  </button>
                  <p className="text-[10px] text-center text-neutral-500">
                    Instantly synthesizes 3D OpenBIM model with CAD components, MEP layers and materials
                  </p>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
