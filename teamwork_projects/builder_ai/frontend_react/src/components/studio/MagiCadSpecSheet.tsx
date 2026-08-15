import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Droplets, Wind, ShieldCheck, FileSpreadsheet, X, CheckCircle2, Activity, Cpu } from 'lucide-react';

interface MagiCadSpecSheetProps {
  isOpen: boolean;
  onClose: () => void;
  isLightMode?: boolean;
}

export const MagiCadSpecSheet: React.FC<MagiCadSpecSheetProps> = ({
  isOpen,
  onClose,
  isLightMode = false,
}) => {
  const mepSystems = [
    {
      title: "Sanitary Soil & Drainage Stack",
      type: "IfcFlowSegment (Drainage)",
      spec: "PVC-U Solvent-Weld High Acoustic Pipe (DN110 / Ø110mm x 3.2mm)",
      metrics: "Capacity: 4.5 L/s gravity discharge",
      compliance: "DIN EN 12056-2 (System I)",
      icon: <Droplets className="w-4 h-4 text-[#06B6D4]" />,
      color: "#06B6D4",
    },
    {
      title: "Potable Domestic Hot & Cold Water",
      type: "IfcFlowSegment (Supply)",
      spec: "Multi-layer Composite PE-RT / AL / PE-RT (DN25 / Ø25mm)",
      metrics: "Pressure: PN16 @ 70°C (2.8 bar operating)",
      compliance: "WRAS / DVGW Certified",
      icon: <Droplets className="w-4 h-4 text-[#38BDF8]" />,
      color: "#38BDF8",
    },
    {
      title: "Electrical High-Voltage Distribution",
      type: "IfcElectricDistributionBoard",
      spec: "3-Phase 415V 200A Main Switchboard with Type 2 SPD",
      metrics: "Circuits: 24 Miniature RCBO (30mA residual)",
      compliance: "IEC 61439-2 / NEC 2026",
      icon: <Zap className="w-4 h-4 text-[#F59E0B]" />,
      color: "#F59E0B",
    },
    {
      title: "HVAC Chilled Air Handling & Chillers",
      type: "IfcUnitaryEquipment",
      spec: "Variable Refrigerant Flow (VRF) Rooftop Heat Pump (28 kW)",
      metrics: "Airflow: 1,400 CFM Galvanized Ducts (300mm x 150mm)",
      compliance: "ASHRAE 90.1 (SEER 18.5)",
      icon: <Wind className="w-4 h-4 text-[#10B981]" />,
      color: "#10B981",
    },
  ];

  if (!isOpen) return null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: -20 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -20 }}
      className={`absolute top-20 right-4 md:right-28 z-30 w-88 md:w-[420px] p-6 rounded-[32px] border shadow-2xl flex flex-col gap-4 max-h-[82vh] overflow-y-auto ${
        isLightMode ? 'bg-white/95 border-slate-200 text-slate-900' : 'glass-card border-[#F59E0B]/40 text-white'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-3 border-white/10">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-[#F59E0B]/20 text-[#F59E0B]">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-black tracking-wider">MAGICAD MEP SPEC SHEET</div>
            <div className="text-[10px] opacity-60">DIN EN 12056 / ASHRAE 90.1 Compliant</div>
          </div>
        </div>
        <button onClick={onClose} className="opacity-60 hover:opacity-100 p-1">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* BIM Component List */}
      <div className="flex flex-col gap-3">
        {mepSystems.map((item, idx) => (
          <div
            key={idx}
            className={`p-3.5 rounded-2xl border flex flex-col gap-1.5 transition-all ${
              isLightMode ? 'bg-slate-50 border-slate-200' : 'bg-black/40 border-white/5'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {item.icon}
                <span className={`text-xs font-bold ${isLightMode ? 'text-slate-900' : 'text-white'}`}>{item.title}</span>
              </div>
              <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 opacity-70">
                {item.type}
              </span>
            </div>

            <div className="text-[11px] opacity-80 pl-6">{item.spec}</div>

            <div className="flex items-center justify-between text-[10px] pl-6 pt-1 border-t border-white/5">
              <span className="text-[#38BDF8] font-mono">{item.metrics}</span>
              <div className="flex items-center gap-1 text-[#10B981] font-bold">
                <CheckCircle2 className="w-3 h-3" />
                <span>{item.compliance}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div className={`p-3 rounded-2xl border text-[11px] flex items-center gap-2.5 ${
        isLightMode ? 'bg-slate-100 border-slate-200 text-slate-700' : 'bg-black/50 border-white/5 text-[#8E8F9C]'
      }`}>
        <Activity className="w-4 h-4 text-[#F59E0B] shrink-0" />
        <span>Full 3D MEP calculations automatically synchronized with IfcOpenShell BIM export schema.</span>
      </div>
    </motion.div>
  );
};
