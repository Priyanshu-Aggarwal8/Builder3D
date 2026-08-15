import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight, Box, Layers, Eye, Zap, Shield, ChevronDown, CheckCircle2,
  Grid, MousePointer, Activity, Upload, FileText, Bot, ShieldCheck, Check,
  SplitSquareVertical, Building2, Cpu, Globe, Footprints, Sparkles, Sun, Moon,
  Sliders, ArrowUpRight, Compass, Maximize2, RotateCw, GitBranch, Ruler, Plus, Minus
} from 'lucide-react';
import { ThreeViewport, LightingPreset } from '../components/three/ThreeViewport';
import { FloorplanModal } from '../components/studio/FloorplanModal';
import { BuildingModel, RenderMode } from '../types/model';

interface LandingPageProps {
  model: BuildingModel | null;
  onNavigate: (page: string) => void;
  theme?: 'dark' | 'light';
}

export const LandingPage: React.FC<LandingPageProps> = ({
  model,
  onNavigate,
  theme = 'dark'
}) => {
  const [expandedFaq, setExpandedFaq] = useState<number | null>(0);
  const [showFloorplanModal, setShowFloorplanModal] = useState(false);
  const [heroExplode, setHeroExplode] = useState(0.0);
  const [heroRenderMode, setHeroRenderMode] = useState<RenderMode>('shaded');
  const [heroLighting, setHeroLighting] = useState<LightingPreset>('noon');
  const [activeTypologyTab, setActiveTypologyTab] = useState(0);

  const isLight = theme === 'light';

  const promptPills = [
    { label: "12-Story High-Rise (2BHK + 3BHK)", style: "Japandi Scandinavian" },
    { label: "Modern Minimalist Villa with Pool", style: "Luxury Calacatta" },
    { label: "Commercial Tech Campus with MEP", style: "Industrial Loft" },
  ];

  const typologies = [
    {
      id: "highrise",
      title: "12-Story Residential High-Rise",
      subtitle: "Dual 2BHK + 3BHK Floor Plates with Central Core",
      stats: { stories: "12 Levels", far: "3.45 FAR", units: "24 Suites", mep: "DN110 + 415V" },
      desc: "Reinforced concrete structural column grid, high-speed dual elevator shafts, pressurized emergency stairwell core, perimeter low-E double glazed curtain walls, and cantilevered sunset balconies."
    },
    {
      id: "villa",
      title: "Luxury Minimalist Cantilever Villa",
      subtitle: "Open-Concept Great Room & Master Wing",
      stats: { stories: "2 Levels", far: "0.85 FAR", area: "680 m²", mep: "Full HVAC + Solar" },
      desc: "Massive open-concept living pavilion, Calacatta marble waterfall chef kitchen, floating steel stringer staircase, master suite with en-suite spa bath, and infinity edge pool deck."
    },
    {
      id: "commercial",
      title: "Commercial Innovation Campus",
      subtitle: "Podium Structure with Dedicated MEP Chases",
      stats: { stories: "6 Levels", far: "2.80 FAR", area: "14,200 m²", mep: "VRF Chiller Plant" },
      desc: "Open-plan corporate floor plates, column-free interior spans, double-height central atrium, subterranean parking matrix, and rooftop solar photovoltaic array."
    }
  ];

  const features = [
    {
      num: "01",
      title: "Multi-Story OpenBIM Synthesis",
      subtitle: "Autonomous procedural generation of multi-story towers, elevator cores, stairwells, and unit partitions (2BHK / 3BHK) without arbitrary placeholders.",
      icon: <Building2 className="w-5 h-5 stroke-[1.5]" />,
    },
    {
      num: "02",
      title: "Interactive AI Architect Agent",
      subtitle: "Multi-turn consultation engine coordinating structural framing, prompt-tailored interior finishes (Japandi, Calacatta, Loft), and vertical MEP risers.",
      icon: <Bot className="w-5 h-5 stroke-[1.5]" />,
    },
    {
      num: "03",
      title: "In-Depth Floor & Room Walkthrough",
      subtitle: "Isolate individual story levels, inspect room partition dimensions, and step inside suites with first-person WASD walk controls.",
      icon: <Footprints className="w-5 h-5 stroke-[1.5]" />,
    },
    {
      num: "04",
      title: "MagiCAD MEP & IfcOpenShell BIM",
      subtitle: "ISO 10303-21 IFC4 schema export with routed 110mm PVC drainage stacks, 3-phase 415V electrical busbars, and VRF heat pumps.",
      icon: <Cpu className="w-5 h-5 stroke-[1.5]" />,
    },
  ];

  const faqs = [
    {
      num: "01",
      q: "How does the Meta-Agent architectural pipeline synthesize 3D models?",
      a: "The Meta-Agent parses your exact natural language prompt to determine building typology, floor count, unit programming (2BHK/3BHK), and aesthetic finish. It coordinates sub-agents to construct structural slabs, partition walls, interior furnishings, and MEP risers without injecting unrequested amenities.",
    },
    {
      num: "02",
      q: "How does in-place conversational customization work?",
      a: "You can conversationally adjust materials, move walls, change room layouts, or add rooftop amenities in real time. Changes mutate the active model state incrementally without scrapping previous work, and are immediately persisted in the database.",
    },
    {
      num: "03",
      q: "Can I inspect and edit individual floors & unit suites in depth?",
      a: "Yes. By selecting the Storey level or opening the Floor Suite, you can isolate any single floor, zoom into its floor plate, add room partition walls, modify element dimensions, or enter first-person walkthrough mode.",
    },
    {
      num: "04",
      q: "Can I upload government approved PDF blueprints & CAD drawings?",
      a: "Yes! BuilderAI accepts PDF blueprints and CAD floor plans, automatically extruding wall vectors, room boundaries, door openings, and wet stacks into volumetric 3D models.",
    },
    {
      num: "05",
      q: "How does the OpenBIM ISO 10303-21 IFC4 export work?",
      a: "BuilderAI uses IfcOpenShell to compile native ISO 10303-21 IFC4 files containing complete IfcBuildingStorey spatial hierarchies, IfcWall, IfcSlab, IfcDoor, and IfcFlowSegment MEP layers ready for Revit, Archicad, and BlenderBIM.",
    },
    {
      num: "06",
      q: "What engineering MEP standards are calculated?",
      a: "Vertical utility risers follow DIN EN 12056-2 drainage stack velocities, ASHRAE 90.1 3-phase 415V electrical busbars, and VRF heat pump ventilation matrices.",
    },
  ];

  return (
    <div className={`w-full flex flex-col items-center pt-28 pb-20 overflow-hidden transition-colors duration-200 ${
      isLight ? 'bg-white text-black' : 'bg-black text-white'
    }`}>
      {/* 1. HERO SECTION (Full-Bleed Adaptive Span) */}
      <section className="w-full px-6 md:px-16 lg:px-24 xl:px-32 flex flex-col items-center text-center">
        {/* Animated Minimal Pill Badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-mono tracking-wider uppercase mb-8 shadow-sm ${
            isLight ? 'bg-white border-black/80 text-black' : 'bg-black border-white/20 text-white'
          }`}
        >
          <span className={`w-2 h-2 rounded-full animate-pulse ${isLight ? 'bg-black' : 'bg-white'}`} />
          <span>OpenBIM 2.4 • IfcOpenShell & Meta-Agent Engine</span>
        </motion.div>

        {/* Hero Title */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-4xl sm:text-6xl md:text-8xl lg:text-9xl font-black tracking-tight uppercase leading-[0.92] max-w-7xl"
        >
          Autonomous 3D <br />
          Architectural BIM
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-6 text-sm sm:text-base md:text-lg lg:text-xl max-w-3xl opacity-70 leading-relaxed font-normal"
        >
          Synthesize multi-story towers, dedicated 2BHK/3BHK floor suites, and compliant MEP engineering systems in real-time WebGL.
        </motion.p>

        {/* Action CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="flex flex-wrap items-center justify-center gap-4 mt-8"
        >
          <button
            onClick={() => onNavigate('studio')}
            className={`flex items-center gap-2.5 px-9 py-4 rounded-full font-black text-xs md:text-sm uppercase tracking-wider transition-transform hover:scale-105 active:scale-95 shadow-xl cursor-pointer ${
              isLight ? 'bg-black text-white hover:bg-neutral-800' : 'bg-white text-black hover:bg-neutral-200'
            }`}
          >
            <span>Launch 3D Studio & Copilot</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </button>
          <button
            onClick={() => setShowFloorplanModal(true)}
            className={`flex items-center gap-2.5 px-8 py-4 rounded-full font-bold text-xs md:text-sm uppercase tracking-wider border transition-all cursor-pointer ${
              isLight
                ? 'bg-white border-black/80 hover:bg-neutral-100 text-black'
                : 'bg-black border-white/20 hover:bg-neutral-900 text-white'
            }`}
          >
            <Upload className="w-4 h-4 stroke-[1.75]" />
            <span>Upload Floor Plan PDF</span>
          </button>
        </motion.div>

        {/* Prompt Quick Launch Pills */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex items-center justify-center flex-wrap gap-2.5 mt-8"
        >
          <span className="text-[10px] font-mono uppercase tracking-wider opacity-40 mr-1">Quick Prompts:</span>
          {promptPills.map((pill, idx) => (
            <button
              key={idx}
              onClick={() => onNavigate('studio')}
              className={`px-4 py-1.5 rounded-full text-xs font-bold border transition-all ${
                isLight
                  ? 'bg-neutral-50 border-neutral-200 hover:border-black text-neutral-800'
                  : 'bg-neutral-950 border-neutral-800 hover:border-white text-neutral-300'
              }`}
            >
              <span>{pill.label}</span>
              <span className="opacity-40 ml-1.5 font-mono text-[10px]">({pill.style})</span>
            </button>
          ))}
        </motion.div>
      </section>

      {/* 2. FULL-BLEED INTERACTIVE 3D HERO STAGE */}
      <section className="w-full px-6 md:px-16 lg:px-24 xl:px-32 mt-12">
        <div className={`w-full h-[520px] sm:h-[640px] rounded-[36px] border overflow-hidden relative shadow-2xl transition-colors ${
          isLight ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-950 border-neutral-800'
        }`}>
          <ThreeViewport
            model={model}
            explodeRatio={heroExplode}
            renderMode={heroRenderMode}
            lightingPreset={heroLighting}
            theme={theme}
            interactive={true}
          />

          {/* Top Left Floating Pill: Engine Status */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className={`absolute top-5 left-5 z-10 px-4 py-2 rounded-full border text-xs font-mono flex items-center gap-2 backdrop-blur-md shadow-lg pointer-events-auto ${
              isLight ? 'bg-white/90 border-black/80 text-black' : 'bg-black/90 border-white/20 text-white'
            }`}
          >
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>WebGL 3D Engine • 120 FPS Active</span>
          </motion.div>

          {/* Top Right Floating Controls: Render Mode */}
          <div className="absolute top-5 right-5 z-10 flex items-center gap-2 pointer-events-auto">
            <div className={`p-1.5 rounded-full border flex items-center gap-1 backdrop-blur-md shadow-lg ${
              isLight ? 'bg-white/90 border-black/80' : 'bg-black/90 border-white/20'
            }`}>
              {(['shaded', 'wireframe', 'xray'] as RenderMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setHeroRenderMode(mode)}
                  className={`px-3.5 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all ${
                    heroRenderMode === mode
                      ? isLight ? 'bg-black text-white' : 'bg-white text-black'
                      : isLight ? 'text-neutral-600 hover:text-black' : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          {/* Bottom Floating Controls: Explode Slabs Slider & Launch CTA */}
          <div className="absolute bottom-5 inset-x-5 md:inset-x-8 z-10 flex flex-col sm:flex-row items-center justify-between gap-3 pointer-events-none">
            {/* Explode Slabs Slider */}
            <div className={`p-2.5 px-5 rounded-full border flex items-center gap-3.5 backdrop-blur-md shadow-lg pointer-events-auto ${
              isLight ? 'bg-white/90 border-black/80 text-black' : 'bg-black/90 border-white/20 text-white'
            }`}>
              <span className="text-[11px] font-mono font-bold uppercase opacity-60">Explode Slabs:</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={heroExplode}
                onChange={(e) => setHeroExplode(parseFloat(e.target.value))}
                className="w-32 sm:w-44 accent-black dark:accent-white cursor-pointer"
              />
              <span className="text-xs font-mono font-bold">{(heroExplode * 100).toFixed(0)}%</span>
            </div>

            {/* Launch Studio Button */}
            <button
              onClick={() => onNavigate('studio')}
              className={`flex items-center gap-2 px-6 py-3 rounded-full font-black text-xs uppercase tracking-wider shadow-xl hover:scale-105 transition-transform pointer-events-auto cursor-pointer ${
                isLight ? 'bg-black text-white' : 'bg-white text-black'
              }`}
            >
              <span>Open in Full Studio</span>
              <ArrowRight className="w-4 h-4 stroke-[2.5]" />
            </button>
          </div>
        </div>
      </section>

      {/* 3. FULL-BLEED INTERACTIVE TYPOLOGY SHOWCASE */}
      <section className="w-full px-6 md:px-16 lg:px-24 xl:px-32 mt-28 flex flex-col gap-10">
        <div className="flex flex-col items-start gap-2">
          <span className="text-xs font-mono uppercase tracking-widest opacity-60">Architecture Typologies</span>
          <h2 className="text-2xl sm:text-4xl md:text-5xl font-black uppercase tracking-tight">
            High-Fidelity Procedural Synthesis
          </h2>
        </div>

        {/* Tab Headers */}
        <div className={`flex items-center gap-2 p-1.5 rounded-full border w-fit max-w-full overflow-x-auto ${
          isLight ? 'bg-neutral-100 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
        }`}>
          {typologies.map((t, idx) => (
            <button
              key={t.id}
              onClick={() => setActiveTypologyTab(idx)}
              className={`px-6 py-2.5 rounded-full text-xs md:text-sm font-bold transition-all whitespace-nowrap cursor-pointer ${
                activeTypologyTab === idx
                  ? isLight ? 'bg-black text-white shadow-sm' : 'bg-white text-black shadow-sm'
                  : isLight ? 'text-neutral-600 hover:text-black' : 'text-neutral-400 hover:text-white'
              }`}
            >
              {t.title}
            </button>
          ))}
        </div>

        {/* Active Tab Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTypologyTab}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -15 }}
            transition={{ duration: 0.3 }}
            className={`p-8 md:p-12 lg:p-14 rounded-[36px] border shadow-xl flex flex-col lg:flex-row items-start lg:items-center justify-between gap-10 ${
              isLight ? 'bg-white border-neutral-200' : 'bg-black border-neutral-800'
            }`}
          >
            <div className="flex flex-col gap-4 max-w-2xl">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${isLight ? 'bg-black' : 'bg-white'}`} />
                <span className="text-xs font-mono uppercase tracking-wider opacity-60">
                  {typologies[activeTypologyTab].subtitle}
                </span>
              </div>
              <h3 className="text-2xl sm:text-3xl md:text-4xl font-black uppercase tracking-tight">
                {typologies[activeTypologyTab].title}
              </h3>
              <p className="text-xs sm:text-base opacity-70 leading-relaxed font-normal">
                {typologies[activeTypologyTab].desc}
              </p>
              <button
                onClick={() => onNavigate('studio')}
                className={`flex items-center gap-2 px-7 py-3 rounded-full font-bold text-xs uppercase tracking-wider w-fit mt-2 border transition-transform hover:scale-105 cursor-pointer ${
                  isLight ? 'bg-black text-white border-black' : 'bg-white text-black border-white'
                }`}
              >
                <span>Synthesize in Studio</span>
                <ArrowRight className="w-3.5 h-3.5 stroke-[2]" />
              </button>
            </div>

            {/* Stats Matrix */}
            <div className="grid grid-cols-2 gap-3.5 w-full lg:w-96">
              {Object.entries(typologies[activeTypologyTab].stats).map(([k, v]) => (
                <div
                  key={k}
                  className={`p-5 rounded-2xl border flex flex-col gap-1 ${
                    isLight ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-900 border-neutral-800'
                  }`}
                >
                  <span className="text-[10px] font-mono uppercase opacity-50">{k}</span>
                  <span className="text-base font-mono font-black">{v}</span>
                </div>
              ))}
            </div>
          </motion.div>
        </AnimatePresence>
      </section>

      {/* 4. FULL-BLEED 2D PDF SCANNER TO 3D SHOWCASE */}
      <section className="w-full px-6 md:px-16 lg:px-24 xl:px-32 mt-28">
        <div className={`p-8 md:p-14 lg:p-16 rounded-[40px] border flex flex-col lg:flex-row items-center justify-between gap-12 relative overflow-hidden ${
          isLight ? 'bg-neutral-50 border-neutral-200' : 'bg-neutral-950 border-neutral-800'
        }`}>
          <div className="flex flex-col gap-4 max-w-xl z-10">
            <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider opacity-60">
              <FileText className="w-4 h-4 stroke-[1.75]" />
              <span>Municipal Blueprint Vector Extruder</span>
            </div>
            <h2 className="text-2xl sm:text-4xl md:text-5xl font-black uppercase tracking-tight leading-tight">
              Turn Govt-Approved PDFs into Volumetric 3D Models
            </h2>
            <p className="text-xs sm:text-base opacity-70 leading-relaxed font-normal">
              BuilderAI analyzes setback requirements, wall thicknesses, door swings, and room dimensions from municipal drawings, extruding them into native IFC4 BIM geometry with zero manual modeling.
            </p>
            <button
              onClick={() => setShowFloorplanModal(true)}
              className={`flex items-center gap-2 px-8 py-4 rounded-full font-black text-xs md:text-sm uppercase tracking-wider w-fit mt-2 transition-transform hover:scale-105 cursor-pointer ${
                isLight ? 'bg-black text-white' : 'bg-white text-black'
              }`}
            >
              <Upload className="w-4 h-4 stroke-[2]" />
              <span>Upload PDF Blueprint</span>
            </button>
          </div>

          {/* Interactive Laser Scanning Simulation Card */}
          <div className={`w-full lg:w-[460px] p-8 rounded-3xl border relative overflow-hidden flex flex-col gap-5 shadow-2xl ${
            isLight ? 'bg-white border-neutral-200 text-black' : 'bg-black border-neutral-800 text-white'
          }`}>
            {/* Animated Laser Scan Bar */}
            <motion.div
              animate={{ y: [0, 220, 0] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
              className="absolute left-0 right-0 h-0.5 bg-neutral-900 dark:bg-white shadow-[0_0_12px_rgba(255,255,255,0.8)] z-20"
            />

            <div className="flex items-center justify-between border-b pb-3.5 border-neutral-200 dark:border-neutral-800">
              <span className="text-xs font-mono font-bold uppercase">MUNICIPAL_DRAWING_L1.PDF</span>
              <span className="text-[10px] font-mono px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">OCR VERIFIED</span>
            </div>

            <div className="flex flex-col gap-2.5 font-mono text-xs">
              <div className="flex justify-between py-1 border-b border-neutral-100 dark:border-neutral-900">
                <span className="opacity-60">Wall Vectors Extracted:</span>
                <span className="font-bold">24 Partitions</span>
              </div>
              <div className="flex justify-between py-1 border-b border-neutral-100 dark:border-neutral-900">
                <span className="opacity-60">Door Openings Detected:</span>
                <span className="font-bold">8 Swings</span>
              </div>
              <div className="flex justify-between py-1 border-b border-neutral-100 dark:border-neutral-900">
                <span className="opacity-60">Plumbing Wet Wall:</span>
                <span className="font-bold">DN110 Riser Match</span>
              </div>
              <div className="flex justify-between py-1">
                <span className="opacity-60">IFC4 Volumetric Conversion:</span>
                <span className="font-bold text-emerald-500">100% Ready</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 5. FULL-BLEED CORE ARCHITECTURAL CAPABILITIES */}
      <section className="w-full px-6 md:px-16 lg:px-24 xl:px-32 mt-28 flex flex-col gap-8">
        <div className="flex flex-col items-start gap-2">
          <span className="text-xs font-mono uppercase tracking-widest opacity-60">Engine Capabilities</span>
          <h2 className="text-2xl sm:text-4xl md:text-5xl font-black uppercase tracking-tight">
            Engineered for Architects & Structural Engineers
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {features.map((item) => (
            <div
              key={item.num}
              className={`p-8 md:p-10 rounded-3xl border flex flex-col justify-between gap-6 transition-all group ${
                isLight
                  ? 'bg-white border-neutral-200 hover:border-black'
                  : 'bg-black border-neutral-800 hover:border-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className={`p-3.5 rounded-2xl border transition-colors ${
                  isLight
                    ? 'border-neutral-200 group-hover:bg-black group-hover:text-white'
                    : 'border-neutral-800 group-hover:bg-white group-hover:text-black'
                }`}>
                  {item.icon}
                </div>
                <span className="font-mono text-xs font-bold opacity-40">{item.num}</span>
              </div>

              <div className="flex flex-col gap-2">
                <h3 className="text-lg md:text-xl font-black tracking-tight uppercase">{item.title}</h3>
                <p className="text-xs sm:text-sm opacity-70 leading-relaxed font-normal">{item.subtitle}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 6. FULL-BLEED FAQ SECTION (Redesigned Template Matching Capabilities & Full Width) */}
      <section className="w-full px-6 md:px-16 lg:px-24 xl:px-32 mt-28 flex flex-col gap-8">
        <div className="flex flex-col items-start gap-2">
          <span className="text-xs font-mono uppercase tracking-widest opacity-60">Knowledge Base</span>
          <h2 className="text-2xl sm:text-4xl md:text-5xl font-black uppercase tracking-tight">
            Frequently Asked Questions
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 w-full">
          {faqs.map((faq, idx) => {
            const isExpanded = expandedFaq === idx;
            return (
              <div
                key={faq.num}
                className={`p-7 md:p-9 rounded-3xl border flex flex-col justify-between transition-all cursor-pointer ${
                  isLight
                    ? (isExpanded ? 'bg-white border-black shadow-lg' : 'bg-neutral-50 border-neutral-200 hover:border-black/50')
                    : (isExpanded ? 'bg-black border-white shadow-lg' : 'bg-neutral-950 border-neutral-800 hover:border-white/50')
                }`}
                onClick={() => setExpandedFaq(isExpanded ? null : idx)}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold opacity-40">{faq.num}</span>
                    <h3 className="text-base sm:text-lg font-black uppercase tracking-tight leading-snug">
                      {faq.q}
                    </h3>
                  </div>
                  <div className={`p-2 rounded-full border shrink-0 transition-transform ${
                    isLight ? 'border-neutral-300' : 'border-neutral-700'
                  }`}>
                    {isExpanded ? <Minus className="w-3.5 h-3.5 stroke-[2]" /> : <Plus className="w-3.5 h-3.5 stroke-[2]" />}
                  </div>
                </div>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0, marginTop: 0 }}
                      animate={{ height: 'auto', opacity: 1, marginTop: 16 }}
                      exit={{ height: 0, opacity: 0, marginTop: 0 }}
                      transition={{ duration: 0.25 }}
                      className="overflow-hidden border-t pt-4 border-neutral-200 dark:border-neutral-800"
                    >
                      <p className="text-xs sm:text-sm opacity-70 leading-relaxed font-normal">
                        {faq.a}
                      </p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </section>

      {/* Floorplan PDF Extruder Modal */}
      <FloorplanModal
        isOpen={showFloorplanModal}
        onClose={() => setShowFloorplanModal(false)}
        onApplyModel={(m) => {
          onNavigate('studio');
        }}
      />
    </div>
  );
};
