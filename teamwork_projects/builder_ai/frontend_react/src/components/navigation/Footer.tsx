import React from 'react';
import { ArrowUpRight, Globe, Layers, Cpu, ShieldCheck } from 'lucide-react';

interface FooterProps {
  onNavigate: (page: string) => void;
  theme?: 'dark' | 'light';
}

export const Footer: React.FC<FooterProps> = ({ onNavigate, theme = 'dark' }) => {
  const isLight = theme === 'light';

  return (
    <footer className={`w-full border-t transition-colors duration-200 py-16 px-6 md:px-16 lg:px-24 xl:px-32 ${
      isLight ? 'bg-white border-neutral-200 text-black' : 'bg-black border-neutral-800 text-white'
    }`}>
      <div className="w-full flex flex-col gap-12">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-10">
          {/* Brand & Manifesto */}
          <div className="md:col-span-2 flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className={`w-2.5 h-2.5 rounded-full ${isLight ? 'bg-black' : 'bg-white'}`} />
              <span className="font-black text-sm tracking-[0.25em] uppercase">
                BUILDER.AI
              </span>
              <span className={`px-2.5 py-0.5 text-[9px] font-mono font-bold tracking-wider rounded uppercase border ${
                isLight ? 'bg-neutral-100 border-neutral-300 text-black' : 'bg-neutral-900 border-neutral-800 text-white'
              }`}>
                OpenBIM 2.4
              </span>
            </div>
            <p className="text-xs opacity-70 leading-relaxed max-w-md font-normal">
              Autonomous architectural BIM synthesis engine. Transforming natural language prompts and municipal PDF blueprints into ISO 10303-21 compliant 3D models with structural, interior, and MEP engineering systems.
            </p>
            <div className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border w-fit mt-2 ${
              isLight ? 'bg-neutral-50 border-neutral-200 text-neutral-800' : 'bg-neutral-900 border-neutral-800 text-neutral-300'
            }`}>
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-mono font-bold">
                IfcOpenShell & Web-IFC Engine Online • 120 FPS
              </span>
            </div>
          </div>

          {/* Column 2: Platform */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-black tracking-wider uppercase opacity-40">Platform</span>
            <button onClick={() => onNavigate('studio')} className="text-xs opacity-70 hover:opacity-100 text-left transition-opacity flex items-center justify-between group cursor-pointer">
              <span>3D CAD Studio</span>
              <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
            <button onClick={() => onNavigate('compliance')} className="text-xs opacity-70 hover:opacity-100 text-left transition-opacity flex items-center justify-between group cursor-pointer">
              <span>Municipal Compliance</span>
              <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
            <button onClick={() => onNavigate('landing')} className="text-xs opacity-70 hover:opacity-100 text-left transition-opacity flex items-center justify-between group cursor-pointer">
              <span>Overview & Architecture</span>
              <ArrowUpRight className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </div>

          {/* Column 3: Standards & Formats */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-black tracking-wider uppercase opacity-40">Standards</span>
            <span className="text-xs opacity-70">ISO 10303-21 IFC4</span>
            <span className="text-xs opacity-70">DIN EN 12056-2 Drainage</span>
            <span className="text-xs opacity-70">ASHRAE 90.1 Electrical</span>
            <span className="text-xs opacity-70">Speckle 3D Versioning</span>
          </div>

          {/* Column 4: Engine */}
          <div className="flex flex-col gap-3">
            <span className="text-xs font-black tracking-wider uppercase opacity-40">Engine</span>
            <span className="text-xs opacity-70">IfcOpenShell Backend</span>
            <span className="text-xs opacity-70">Three.js & ThatOpen WebGL</span>
            <span className="text-xs opacity-70">Meta-Agent Architecture</span>
            <span className="text-xs opacity-70">First-Person Walkthrough</span>
          </div>
        </div>

        {/* Bottom Metadata Bar */}
        <div className="pt-8 border-t border-neutral-200 dark:border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs opacity-60">
          <span>© 2026 BuilderAI Inc. Engineered for Architects, Engineers, and Constructors.</span>
          <div className="flex items-center gap-6 text-[11px] font-mono">
            <span>IFC4 STANDARD</span>
            <span>•</span>
            <span>OPENBIM CERTIFIED</span>
            <span>•</span>
            <span>PRIVACY & SECURITY</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
