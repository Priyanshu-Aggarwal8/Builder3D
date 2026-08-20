import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles, Send, Bot, User, ChevronRight, RefreshCw,
  Building, Layers, Zap, X, ArrowUpRight
} from 'lucide-react';
import { BuildingModel } from '../../types/model';
import { sanitizeBuildingModel } from '../../services/api';

interface Message {
  id: string;
  sender: 'agent' | 'user';
  text: string;
  timestamp: string;
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
      text: "Welcome! I am your **Principal AI Architect & OpenBIM Copilot**.\n\nDescribe your building project in freeform natural language, or ask me to modify the active 3D model in real-time.\n\n• **Example 1**: *\"Design a 12-storey Grade-A commercial office tower with central core, workstation clusters, executive boardroom, and full MEP systems\"*\n• **Example 2**: *\"Create a 2-storey luxury modern villa with cantilevered balconies and swimming pool\"*\n• **Example 3**: *\"Upgrade active facade to triple-glazed Low-E glass with dark aluminum mullions\"*",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      quickActions: [
        "12-Storey Commercial Tower",
        "3-Storey Modern Villa",
        "Upgrade to Calacatta Marble",
        "Add Rooftop Chiller & Solar"
      ]
    },
  ]);

  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [liveBrief, setLiveBrief] = useState<Record<string, any>>({
    project_name: "Active Architectural Model",
    floors: 12,
    typology: "Commercial / Residential",
    interior_style: "Contemporary Modern",
  });

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (model) {
      const entityCount = Object.values(model.layers || {}).reduce(
        (acc, l) => acc + (l.elements || []).length,
        0
      );
      const floors = model.meta?.floors || 12;
      const style = model.meta?.style || "Contemporary Modern";

      setLiveBrief({
        project_name: model.name || `${floors}-Story Building`,
        floors: floors,
        interior_style: style,
        typology: model.meta?.typology || "OpenBIM Model",
      });

      setMessages((prev) => {
        if (prev.length <= 1) {
          return [
            {
              id: 'msg_active_model',
              sender: 'agent',
              text: `Managing active model: **${model.name || 'Building'}** (${floors} Levels • ${entityCount} BIM elements).\n\nType any natural language instruction to customize floorplates, adjust facade systems, add amenities, or inspect MEP layers.`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              quickActions: [
                "Upgrade to Luxury Calacatta Marble",
                "Add Rooftop Chiller & Solar Array",
                "Isolate Level 1 Storey",
                "Export ISO 10303-21 IFC4"
              ]
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

  // Markdown Formatter: Renders **bold**, *italic*, headers, and bullets cleanly
  const renderFormattedText = (text: string) => {
    const lines = text.split('\n');
    return lines.map((line, lIdx) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('### ')) {
        return (
          <div key={lIdx} className="font-bold text-[13px] text-current mt-2 mb-1 border-b pb-0.5 opacity-90">
            {trimmed.slice(4)}
          </div>
        );
      }
      if (trimmed.startsWith('## ')) {
        return (
          <div key={lIdx} className="font-black text-sm text-current mt-2.5 mb-1 opacity-95">
            {trimmed.slice(3)}
          </div>
        );
      }

      const isBullet = trimmed.startsWith('•') || trimmed.startsWith('-');
      const cleanLine = isBullet ? trimmed.replace(/^[•\-]\s*/, '') : line;

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
            <span className="opacity-40 text-[10px] select-none shrink-0">•</span>
            <span className="flex-1">{formattedContent}</span>
          </div>
        );
      }

      return (
        <div key={lIdx} className={trimmed === '' ? 'h-2' : 'my-0.5'}>
          {formattedContent}
        </div>
      );
    });
  };

  // Send turn to backend conversational agent
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

      const agentMessage: Message = {
        id: `agent_${Date.now()}`,
        sender: 'agent',
        text: data.message || "Recorded specifications.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        quickActions: data.quick_actions || [],
        briefSnapshot: data.brief,
      };

      setMessages((prev) => [...prev, agentMessage]);

      if (data.model && !data.is_inquiry) {
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
          text: `Applied instruction: "${text}". Real-time model updated in 3D canvas.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
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
        className={`fixed left-4 top-20 bottom-24 w-[430px] max-w-[calc(100vw-32px)] z-40 rounded-3xl border shadow-2xl flex flex-col overflow-hidden backdrop-blur-xl transition-colors ${
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
              <span className="text-[10px] font-mono opacity-60">Autonomous OpenBIM & Spatial Copilot</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => handleSendTurn("Synthesize a high-precision 3D OpenBIM model based on active specifications", true)}
              disabled={isProcessing}
              className={`px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider border transition-transform hover:scale-105 active:scale-95 flex items-center gap-1 cursor-pointer ${
                isLightMode
                  ? 'bg-black text-white border-black hover:bg-neutral-800'
                  : 'bg-white text-black border-white hover:bg-neutral-200'
              }`}
              title="Synthesize 3D model immediately"
            >
              <Sparkles className="w-3 h-3 stroke-[2.5]" />
              <span>Generate</span>
            </button>
            <button onClick={onClose} className="p-1.5 opacity-60 hover:opacity-100 transition-opacity cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Live Project Brief Header */}
        <div className={`px-4 py-2 border-b flex items-center justify-between text-[11px] font-mono ${
          isLightMode ? 'bg-neutral-100/80 border-neutral-200' : 'bg-neutral-900/80 border-neutral-800'
        }`}>
          <div className="flex items-center gap-2 truncate max-w-[270px]">
            <span className="opacity-50">Active:</span>
            <span className="font-bold truncate">{liveBrief.project_name || 'Building'} ({liveBrief.floors}F)</span>
          </div>
          <span className="font-bold uppercase text-[9px] px-2 py-0.5 rounded border border-current">
            {liveBrief.interior_style || 'Modern'}
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

                {/* Quick Action Suggestions */}
                {isAgent && msg.quickActions && msg.quickActions.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 ml-8 mt-1">
                    {msg.quickActions.map((actionText, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendTurn(actionText)}
                        disabled={isProcessing}
                        className={`text-left px-2.5 py-1 rounded-full text-[10px] font-mono border transition-all flex items-center gap-1 cursor-pointer ${
                          isLightMode
                            ? 'bg-white border-neutral-200 hover:border-black hover:bg-neutral-50 text-neutral-800'
                            : 'bg-neutral-950 border-neutral-800 hover:border-white hover:bg-neutral-900 text-neutral-200'
                        }`}
                      >
                        <span>{actionText}</span>
                        <ArrowUpRight className="w-2.5 h-2.5 opacity-50" />
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
              <span>Architectural AI synthesizing 3D model & spatial graph...</span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <div className={`p-3 border-t flex flex-col gap-2 ${
          isLightMode ? 'bg-neutral-50/90 border-neutral-200' : 'bg-neutral-900/90 border-neutral-800'
        }`}>
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
              placeholder="Describe your building (e.g. 12-story commercial tower...)"
              disabled={isProcessing}
              className={`flex-1 px-3.5 py-2.5 rounded-xl text-xs border outline-none font-sans ${
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
