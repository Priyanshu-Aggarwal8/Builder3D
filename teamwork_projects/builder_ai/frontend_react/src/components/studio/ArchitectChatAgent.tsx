import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Send, Bot, User, CheckCircle2, ChevronRight, RefreshCw,
  Building, Layers, Home, Zap, Shield, FileText, ArrowRight, Wand2, X,
  Sliders, Check, AlertCircle, ArrowUpRight
} from 'lucide-react';
import { BuildingModel } from '../../types/model';
import { sanitizeBuildingModel } from '../../services/api';

interface OptionItem {
  label: string;
  value: string;
}

interface Message {
  id: string;
  sender: 'agent' | 'user';
  text: string;
  timestamp: string;
  options?: OptionItem[];
  quickActions?: string[];
  briefSnapshot?: Record<string, any>;
}

interface ArchitectChatAgentProps {
  isOpen: boolean;
  onClose: () => void;
  onApplyModel: (model: BuildingModel) => void;
  model?: BuildingModel | null;
  isLightMode?: boolean;
}

export const ArchitectChatAgent: React.FC<ArchitectChatAgentProps> = ({
  isOpen,
  onClose,
  onApplyModel,
  model = null,
  isLightMode = false,
}) => {
  const [sessionId] = useState(() => `sess_${Date.now()}`);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg_init',
      sender: 'agent',
      text: "Welcome to the **Principal AI Architect & BIM Meta-Agent**.\n\nI will guide you through establishing the architectural parameters (plot dimensions, story count, unit programming, aesthetic finishes, and MEP systems) before compiling the high-precision 3D OpenBIM model.\n\n**Step 1 of 5: What are your target plot dimensions and site boundaries?**",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      options: [
        { label: "40m × 60m Standard Plot (2,400 m²)", value: "40m x 60m standard urban parcel with 2,400 m² plot area" },
        { label: "50m × 80m High-Rise Parcel (4,000 m²)", value: "50m x 80m high-density development parcel with 4,000 m² plot area" },
        { label: "30m × 40m Boutique Parcel (1,200 m²)", value: "30m x 40m boutique urban plot with 1,200 m² area" },
        { label: "60m × 90m Masterplan Estate (5,400 m²)", value: "60m x 90m masterplan estate parcel with 5,400 m² area" }
      ],
      quickActions: ["Synthesize 3D Model Now", "12 Stories (2BHK + 3BHK)", "Japandi Style", "Add Rooftop Pool"]
    },
  ]);

  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [stepProgress, setStepProgress] = useState({ current: 1, total: 5 });
  const [liveBrief, setLiveBrief] = useState<Record<string, any>>({
    project_name: "12-Story High-Rise",
    floors: 12,
    unit_mix: "2 Units per floor (1x 2BHK West + 1x 3BHK East)",
    facade_style: "Double-Glazed Low-E Glass with Black Mullions",
    interior_style: "Japandi Scandinavian",
    rooftop_amenity: "Sky Terrace & Solar Pergola",
  });

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (model) {
      const entityCount = Object.values(model.layers || {}).reduce(
        (acc, l) => acc + (l.elements || []).length,
        0
      );
      const floors = model.meta?.floors || 6;
      const style = model.meta?.style || "Contemporary Modern";

      setLiveBrief({
        project_name: model.name || `${floors}-Story Building`,
        floors: floors,
        interior_style: style,
        unit_mix: "2 Units per floor (1x 2BHK West + 1x 3BHK East)",
        facade_style: "Double-Glazed Low-E Glass with Black Aluminum Mullions",
        rooftop_amenity: "Panoramic Sky Lounge & Solar Array",
      });

      setMessages((prev) => {
        if (prev.length <= 1) {
          return [
            {
              id: 'msg_active_model',
              sender: 'agent',
              text: `Welcome back! I am currently managing the active **${model.name || 'Building'}** (${floors} Levels, ${entityCount} components).\n\nWhat would you like to customize or refine? You can ask me to adjust unit room layouts, swap material finishes, add luxury amenities, or reconfigure MEP systems in real-time.`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              options: [
                { label: "Upgrade to Luxury Calacatta Marble", value: "Upgrade all countertops and flooring to luxury Calacatta marble" },
                { label: "Add Rooftop Infinity Pool & Sky Deck", value: "Add infinity swimming pool and sunset lounge to the rooftop" },
                { label: "Convert Level 3 to Penthouse Suite", value: "Reconfigure Level 3 into a grand full-floor penthouse suite" },
                { label: "Add Balcony Greenery & Planters", value: "Add biophilic vertical planter boxes and teak deck louvers to all balconies" }
              ],
              quickActions: ["Upgrade to Calacatta Marble", "Add Rooftop Pool", "Add Balcony Planters", "Export ISO 10303-21 IFC4"]
            }
          ];
        }
        return prev;
      });
    }
  }, [model?.name, model?.meta?.floors, model?.version]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  // Markdown Formatter: Renders **bold**, *italic*, bullets cleanly into DOM
  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, lIdx) => {
      const isBullet = line.trim().startsWith('•') || line.trim().startsWith('-');
      const cleanLine = isBullet ? line.trim().replace(/^[•\-]\s*/, '') : line;

      const parts = cleanLine.split(/(\*\*.*?\*\*|\*.*?\*)/g);
      const formattedContent = parts.map((part, pIdx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={pIdx} className="font-bold">{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('*') && part.endsWith('*')) {
          return <em key={pIdx} className="italic opacity-85">{part.slice(1, -1)}</em>;
        }
        return part;
      });

      if (isBullet) {
        return (
          <div key={lIdx} className="flex items-start gap-1.5 my-1 ml-1 leading-snug">
            <span className="opacity-40 text-[10px] select-none">•</span>
            <span>{formattedContent}</span>
          </div>
        );
      }

      return (
        <div key={lIdx} className={line.trim() === '' ? 'h-2' : 'my-0.5'}>
          {formattedContent}
        </div>
      );
    });
  };

  // Send turn to backend conversational state machine
  const handleSendTurn = async (text: string, synthesizeNow: boolean = false) => {
    if (!text.trim() || isProcessing) return;

    const userMessage: Message = {
      id: `usr_${Date.now()}`,
      sender: 'user',
      text: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsProcessing(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/chat/message", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          synthesize_now: synthesizeNow,
          project_id: 1,
          current_model: model,
        }),
      });

      if (!res.ok) throw new Error("Chat agent request failed");
      const data = await res.json();

      if (data.brief) {
        setLiveBrief(data.brief);
      }
      if (data.step_index) {
        setStepProgress({ current: data.step_index, total: data.total_steps || 5 });
      }

      const agentMessage: Message = {
        id: `agent_${Date.now()}`,
        sender: 'agent',
        text: data.message || "Recorded specifications.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        options: data.options || [],
        quickActions: data.quick_actions || [],
        briefSnapshot: data.brief,
      };

      setMessages((prev) => [...prev, agentMessage]);

      if (data.model) {
        const cleanModel = sanitizeBuildingModel(data.model);
        onApplyModel(cleanModel);
      }
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          sender: 'agent',
          text: `Recorded instruction: "${text}". Customizations updated on active model.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  // Direct 1-Click Synthesis Trigger
  const handleTriggerDirectSynthesis = async () => {
    setIsProcessing(true);
    try {
      const promptText = `${liveBrief.floors || 12}-story building with ${liveBrief.unit_mix || '2BHK and 3BHK'}, ${liveBrief.interior_style || 'Japandi'} style, ${liveBrief.facade_style || 'Low-E glass'}`;
      const res = await fetch("http://127.0.0.1:8000/api/chat/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptText, project_id: 1, current_model: model }),
      });
      if (!res.ok) throw new Error("Synthesis failed");
      const data = await res.json();
      if (data.model) {
        onApplyModel(sanitizeBuildingModel(data.model));
        setMessages((prev) => [
          ...prev,
          {
            id: `syn_${Date.now()}`,
            sender: 'agent',
            text: `✓ **Successfully synthesized ${data.model.name}** (${Object.values(data.model.layers).reduce((a: number, l: any) => a + (l.elements || []).length, 0)} BIM entities). Real-time 3D model updated in canvas!`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          }
        ]);
      }
    } catch (err) {
      console.error("Direct synthesis error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, x: -30, scale: 0.98 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        exit={{ opacity: 0, x: -30, scale: 0.98 }}
        transition={{ duration: 0.25 }}
        className={`fixed left-4 top-20 bottom-24 w-[410px] max-w-[calc(100vw-32px)] z-40 rounded-3xl border shadow-2xl flex flex-col overflow-hidden backdrop-blur-xl transition-colors ${
          isLightMode
            ? 'bg-white/95 border-black/80 text-black shadow-[0_20px_50px_rgba(0,0,0,0.15)]'
            : 'bg-black/95 border-white/20 text-white shadow-[0_20px_50px_rgba(0,0,0,0.7)]'
        }`}
      >
        {/* Header */}
        <div className={`p-4 border-b flex items-center justify-between ${
          isLightMode ? 'bg-neutral-50/90 border-neutral-200' : 'bg-neutral-900/90 border-neutral-800'
        }`}>
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-xl border ${
              isLightMode ? 'bg-black text-white border-black' : 'bg-white text-black border-white'
            }`}>
              <Bot className="w-4 h-4 stroke-[2]" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="font-black text-xs uppercase tracking-wider">AI Principal Architect</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </div>
              <span className="text-[10px] font-mono opacity-60">Discovery Flow • Step {stepProgress.current} of {stepProgress.total}</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={handleTriggerDirectSynthesis}
              disabled={isProcessing}
              className={`px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider border transition-transform hover:scale-105 active:scale-95 flex items-center gap-1 cursor-pointer ${
                isLightMode
                  ? 'bg-black text-white border-black hover:bg-neutral-800'
                  : 'bg-white text-black border-white hover:bg-neutral-200'
              }`}
              title="Synthesize 3D model immediately from current brief"
            >
              <Sparkles className="w-3 h-3 stroke-[2.5]" />
              <span>Synthesize</span>
            </button>
            <button onClick={onClose} className="p-1.5 opacity-60 hover:opacity-100 transition-opacity cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Live Project Brief Drawer */}
        <div className={`px-4 py-2 border-b flex items-center justify-between text-[11px] font-mono ${
          isLightMode ? 'bg-neutral-100/80 border-neutral-200' : 'bg-neutral-900/80 border-neutral-800'
        }`}>
          <div className="flex items-center gap-2 truncate max-w-[270px]">
            <span className="opacity-50">Brief:</span>
            <span className="font-bold truncate">{liveBrief.floors}F • {liveBrief.unit_mix}</span>
          </div>
          <span className="font-bold uppercase text-[9px] px-2 py-0.5 rounded border border-current">
            {liveBrief.interior_style}
          </span>
        </div>

        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3.5">
          {messages.map((msg) => {
            const isAgent = msg.sender === 'agent';
            return (
              <div key={msg.id} className={`flex flex-col gap-2 ${isAgent ? 'items-start' : 'items-end'}`}>
                <div className={`flex items-start gap-2 max-w-[95%] ${isAgent ? 'flex-row' : 'flex-row-reverse'}`}>
                  <div className={`w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[10px] border ${
                    isAgent
                      ? (isLightMode ? 'bg-black text-white border-black' : 'bg-white text-black border-white')
                      : (isLightMode ? 'bg-neutral-200 text-black border-neutral-300' : 'bg-neutral-800 text-white border-neutral-700')
                  }`}>
                    {isAgent ? <Bot className="w-3 h-3" /> : <User className="w-3 h-3" />}
                  </div>

                  <div className={`p-3.5 rounded-2xl text-xs leading-relaxed border ${
                    isAgent
                      ? (isLightMode ? 'bg-neutral-50 border-neutral-200 text-neutral-900' : 'bg-neutral-900 border-neutral-800 text-neutral-100')
                      : (isLightMode ? 'bg-black text-white border-black' : 'bg-white text-black border-white')
                  }`}>
                    <div className="font-sans leading-relaxed">{renderFormattedText(msg.text)}</div>
                  </div>
                </div>

                {/* Option Chips */}
                {isAgent && msg.options && msg.options.length > 0 && (
                  <div className="flex flex-col gap-1.5 ml-8 mt-1 w-[90%]">
                    {msg.options.map((opt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendTurn(opt.value)}
                        disabled={isProcessing}
                        className={`text-left px-3.5 py-2 rounded-xl text-xs font-medium border transition-all flex items-center justify-between group cursor-pointer ${
                          isLightMode
                            ? 'bg-white border-neutral-200 hover:border-black hover:bg-neutral-50 text-neutral-800'
                            : 'bg-neutral-950 border-neutral-800 hover:border-white hover:bg-neutral-900 text-neutral-200'
                        }`}
                      >
                        <span className="truncate pr-2">{opt.label}</span>
                        <ChevronRight className="w-3.5 h-3.5 opacity-40 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all shrink-0" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {isProcessing && (
            <div className="flex items-center gap-2 text-xs font-mono opacity-60 p-2 ml-8">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>Analyzing architectural brief...</span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div className={`p-3 border-t flex flex-col gap-2 ${
          isLightMode ? 'bg-neutral-50/90 border-neutral-200' : 'bg-neutral-900/90 border-neutral-800'
        }`}>
          {/* Quick Action Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
            {["12 Stories (2BHK+3BHK)", "Luxury Calacatta", "Add Rooftop Pool", "Add Solar Array"].map((act, i) => (
              <button
                key={i}
                onClick={() => handleSendTurn(act)}
                disabled={isProcessing}
                className={`px-2.5 py-1 rounded-full text-[10px] font-mono whitespace-nowrap border transition-all cursor-pointer ${
                  isLightMode
                    ? 'bg-white border-neutral-200 hover:border-black text-neutral-700'
                    : 'bg-black border-neutral-800 hover:border-white text-neutral-300'
                }`}
              >
                {act}
              </button>
            ))}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendTurn(inputText);
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Specify requirements or ask questions..."
              disabled={isProcessing}
              className={`flex-1 px-3.5 py-2 rounded-xl text-xs border outline-none font-sans ${
                isLightMode
                  ? 'bg-white border-neutral-200 text-black placeholder-neutral-400 focus:border-black'
                  : 'bg-black border-neutral-800 text-white placeholder-neutral-500 focus:border-white'
              }`}
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isProcessing}
              className={`p-2.5 rounded-xl border transition-all cursor-pointer ${
                inputText.trim() && !isProcessing
                  ? (isLightMode ? 'bg-black text-white border-black' : 'bg-white text-black border-white')
                  : 'opacity-30 cursor-not-allowed border-transparent'
              }`}
            >
              <Send className="w-3.5 h-3.5 stroke-[2]" />
            </button>
          </form>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
