"use client";

import { Flex, Typography, Badge, Button, Input, Tooltip, Avatar } from "antd";
import React, { useState, useRef, useEffect, useCallback } from "react";
import { LuBot, LuHistory, LuSearch, LuSettings, LuPlus } from "react-icons/lu";
import { FiUser, FiSend, FiAlertCircle, FiMoreVertical, FiTrash2 } from "react-icons/fi";
import { MdBarChart } from "react-icons/md";
import { PiGraphLight } from "react-icons/pi";
import { getCookie } from "../../config/cookies";
import AgentList from "../../components/ui/AgentList";

const { Text, Title } = Typography;

// ─── Types ───────────────────────────────────────────────────────────────────

type Message = {
  role: "user" | "assistant";
  content: string;
  confidence?: number;
  nodes?: number;
  timestamp?: string;
};

type ChatSession = {
  id: string;
  agentId: string;
  agentName: string;
  messages: Message[];
  updatedAt: number;
};

const STORAGE_KEY = "graphmind_chat_history";

export default function ChatPlaygroundPage() {
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  
  const [input, setInput] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [wsStatus, setWsStatus] = useState<"connecting" | "open" | "closed" | "error">("closed");

  const bottomRef = useRef<HTMLDivElement>(null);
  const ws = useRef<WebSocket | null>(null);
  const streamingTextRef = useRef<string>("");
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // ─── Persistence Logic ──────────────────────────────────────────────────────

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) setSessions(parsed);
      } catch (e) {
        console.error("Failed to parse chat history", e);
      }
    }
  }, []);

  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    }
  }, [sessions]);

  useEffect(() => {
    if (currentSessionId && messages.length > 0) {
      setSessions(prev => prev.map(s => 
        s.id === currentSessionId 
          ? { ...s, messages, updatedAt: Date.now() } 
          : s
      ));
    }
  }, [messages, currentSessionId]);

  // ─── WebSocket Logic ────────────────────────────────────────────────────────

  const connectWs = useCallback(() => {
    if (!agent?.id) return;

    if (ws.current) ws.current.close();
    setWsStatus("connecting");
    
    const wsHost = process.env.NEXT_PUBLIC_WS_URL || "ws://192.168.1.10:4915";
    const wsUrl = `${wsHost}/api/v1/rag/ws/${agent.id}?token=${getCookie("AUTH_TOKEN")}`;
    
    const socket = new WebSocket(wsUrl);
    ws.current = socket;

    socket.onopen = () => {
      setWsStatus("open");
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };

    socket.onmessage = (event) => {
      const rawData = String(event.data);
      if (rawData.length === 1 || (!rawData.startsWith("{") && !rawData.startsWith("["))) {
        streamingTextRef.current += rawData;
        setStreamingText(streamingTextRef.current);
        setIsTyping(true);
        return;
      }

      try {
        const data = JSON.parse(rawData);
        if (data.type === "metadata") return;
        if (data.type === "done") {
          const accumulated = streamingTextRef.current;
          if (accumulated) {
            setMessages((prev) => [...prev, { 
              role: "assistant", 
              content: accumulated, 
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
            }]);
          }
          streamingTextRef.current = "";
          setStreamingText("");
          setIsTyping(false);
          return;
        }
        if (data.type === "chunk" || data.type === "delta" || data.type === "content" || data.type === "text") {
          const textChunk = data.message || data.content || data.text || "";
          streamingTextRef.current += textChunk;
          setStreamingText(streamingTextRef.current);
          setIsTyping(true);
          return;
        }
      } catch (err) {
        streamingTextRef.current += rawData;
        setStreamingText(streamingTextRef.current);
        setIsTyping(true);
      }
    };

    socket.onclose = () => {
      setWsStatus("closed");
      if (agent?.id) {
        reconnectTimeoutRef.current = setTimeout(() => connectWs(), 3000);
      }
    };
  }, [agent?.id]);

  useEffect(() => {
    connectWs();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      ws.current?.close();
    };
  }, [connectWs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // ─── Actions ───────────────────────────────────────────────────────────────

  const startNewChat = (selectedAgent: { id: string; name: string }) => {
    const newSessionId = `session_${Date.now()}`;
    const newSession: ChatSession = {
      id: newSessionId,
      agentId: selectedAgent.id,
      agentName: selectedAgent.name,
      messages: [],
      updatedAt: Date.now()
    };
    setSessions(prev => [newSession, ...prev]);
    setCurrentSessionId(newSessionId);
    setMessages([]);
    setAgent(selectedAgent);
  };

  const loadSession = (session: ChatSession) => {
    setCurrentSessionId(session.id);
    setMessages(session.messages);
    setAgent({ id: session.agentId, name: session.agentName });
  };

  const deleteSession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSessions(prev => prev.filter(s => s.id !== id));
    if (currentSessionId === id) {
      setCurrentSessionId(null);
      setMessages([]);
      setAgent(null);
    }
  };

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !agent?.id || wsStatus !== "open") return;

    if (!currentSessionId) {
      const newId = `session_${Date.now()}`;
      const newSession: ChatSession = {
        id: newId,
        agentId: agent.id,
        agentName: agent.name,
        messages: [],
        updatedAt: Date.now()
      };
      setSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(newId);
    }

    setMessages((prev) => [...prev, { 
      role: "user", 
      content: trimmed, 
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
    }]);
    
    setInput("");
    streamingTextRef.current = "";
    setStreamingText("");
    setIsTyping(true);
    ws.current?.send(JSON.stringify({ query: trimmed }));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <div className="h-[calc(100vh-140px)] w-full flex gap-8 animate-in fade-in duration-700">
      
      {/* Left Panel: Real Conversation History */}
      <div className="hidden xl:flex flex-col w-84 bg-[var(--app-surface)]/40 backdrop-blur-md rounded-[32px] border border-[var(--app-border)] shadow-sm overflow-hidden">
        <div className="p-6 border-b border-[var(--app-border)] space-y-4">
          <Flex align="center" justify="space-between">
            <Title level={5} className="!m-0 !text-[#285d91] !font-black uppercase tracking-widest text-[10px]">Chat History</Title>
            <Button 
              type="text" 
              icon={<LuPlus />} 
              onClick={() => { setAgent(null); setCurrentSessionId(null); setMessages([]); }} 
              className="text-[#285d91] hover:bg-[var(--app-active-bg)] rounded-lg"
            />
          </Flex>
          <Input 
            prefix={<LuSearch className="text-[var(--app-text-soft)]" />}
            placeholder="Search threads..."
            className="!rounded-2xl !bg-[var(--app-surface-muted)] !border-none !h-10 font-bold text-xs text-[var(--app-text)] placeholder:text-[var(--app-text-soft)]"
          />
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {sessions.length > 0 ? (
            sessions.map((s) => (
              <div 
                key={s.id} 
                onClick={() => loadSession(s)}
                className={`group relative p-4 rounded-2xl cursor-pointer transition-all border ${
                  currentSessionId === s.id 
                    ? "bg-[#285d91] text-white shadow-lg border-transparent" 
                    : "bg-[var(--app-surface-muted)] hover:bg-[var(--app-hover)] text-[var(--app-text)] border-[var(--app-border)]"
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <Text className={`font-black text-xs block truncate pr-6 ${currentSessionId === s.id ? "text-white" : "text-[var(--app-text)]"}`}>
                    {s.messages.length > 0 ? s.messages[0].content : s.agentName}
                  </Text>
                  <FiTrash2 
                    onClick={(e) => deleteSession(e, s.id)}
                    className={`opacity-0 group-hover:opacity-100 transition-opacity text-xs ${currentSessionId === s.id ? "text-white/50 hover:text-white" : "text-[var(--app-text-soft)] hover:text-red-500"}`} 
                  />
                </div>
                <div className="flex justify-between items-center mt-2">
                  <Text className={`text-[10px] block opacity-60 font-bold ${currentSessionId === s.id ? "text-white/70" : "text-[var(--app-text-muted)]"}`}>
                    {new Date(s.updatedAt).toLocaleDateString()}
                  </Text>
                  <div className={`px-2 py-0.5 rounded-md text-[8px] font-black uppercase tracking-widest ${
                    currentSessionId === s.id ? "bg-white/20 text-white" : "bg-[var(--app-active-bg)] text-[var(--app-text-soft)]"
                  }`}>
                    {s.messages.length} msgs
                  </div>
                </div>
              </div>
            ))
          ) : (
            <Flex vertical align="center" justify="center" className="h-full py-10 opacity-30 text-center">
              <LuHistory size={32} className="text-[#285d91] mb-2" />
              <Text className="font-bold text-[10px] uppercase tracking-widest text-[var(--app-text-muted)]">No local history found</Text>
            </Flex>
          )}
        </div>
      </div>

      {/* Main Chat Panel */}
      <Flex vertical className="flex-1 bg-[var(--app-surface)]/80 backdrop-blur-2xl rounded-[40px] border border-[var(--app-border)] shadow-[0_20px_50px_rgba(40,93,145,0.05)] overflow-hidden">
        
        {/* Chat Header */}
        <Flex justify="space-between" align="center" className="px-10 py-8 border-b border-[var(--app-border)] bg-[var(--app-surface)]/30">
          <Flex align="center" gap={16}>
            <div className="w-14 h-14 rounded-2xl bg-[#285d91] text-white flex items-center justify-center shadow-lg shadow-blue-900/10">
              <LuBot size={28} />
            </div>
            <Flex vertical>
              <Title level={3} className="!m-0 !text-[var(--app-text)] !font-black tracking-tighter">
                {agent?.name || "Neural Assistant"}
              </Title>
              <Flex align="center" gap={6}>
                <Badge status={wsStatus === "open" ? "success" : "processing"} />
                <Text className={`text-[10px] font-black uppercase tracking-[0.2em] ${wsStatus === "open" ? "text-emerald-500" : "text-amber-500"}`}>
                  {wsStatus === "open" ? "Synthesizer Online" : "Connecting Neural Link..."}
                </Text>
              </Flex>
            </Flex>
          </Flex>
          
          <Flex align="center" gap={12}>
            <AgentList
              selectedId={agent?.id}
              onChange={(id: string, name: string) => {
                const existing = sessions.find(s => s.agentId === id);
                if (existing) loadSession(existing);
                else startNewChat({ id, name });
              }}
            />
            <Button type="text" icon={<FiMoreVertical className="text-xl text-[var(--app-text-soft)]" />} />
          </Flex>
        </Flex>

        {/* Chat Stream */}
        <div className="flex-1 overflow-y-auto px-10 py-10 space-y-8 custom-scrollbar">
          {messages.length === 0 && !isTyping && (
            <Flex vertical align="center" justify="center" className="h-full space-y-6 opacity-40">
              <div className="w-24 h-24 rounded-[32px] bg-[var(--app-surface-muted)] flex items-center justify-center relative">
                <div className="absolute inset-0 bg-[#285d91] rounded-[32px] blur-2xl opacity-10 animate-pulse" />
                <LuBot size={48} className="text-[#285d91] relative z-10" />
              </div>
              <div className="text-center">
                <Title level={2} className="!m-0 !text-[var(--app-text)] !font-black !text-3xl tracking-tighter">Initiate Thought Loop</Title>
                <Text className="text-[var(--app-text-muted)] font-bold mt-2 block">Select your AI architect to begin multi-hop reasoning.</Text>
              </div>
            </Flex>
          )}

          {messages.map((msg, i) => (
            <Flex key={i} justify={msg.role === "user" ? "flex-end" : "flex-start"} className="group animate-in slide-in-from-bottom-4 duration-500">
              <div className="flex flex-col max-w-[75%] gap-2">
                <Flex align="center" gap={8} className={`mb-1 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                  <Avatar 
                    icon={msg.role === "user" ? <FiUser /> : <LuBot />} 
                    className={`${msg.role === "user" ? "bg-emerald-500" : "bg-[#285d91]"} shadow-sm`}
                  />
                  <Text className="text-[10px] font-black uppercase tracking-widest text-[var(--app-text-soft)]">{msg.timestamp}</Text>
                </Flex>
                
                <div className={`relative p-6 rounded-[32px] shadow-sm transition-all duration-300 ${
                  msg.role === "user" 
                  ? "bg-[#285d91] text-white rounded-tr-none hover:shadow-blue-900/10" 
                  : "bg-[var(--app-surface)] border border-[var(--app-border)] text-[var(--app-text)] rounded-tl-none hover:shadow-slate-200/50"
                }`}>
                  <p className="text-sm md:text-base font-semibold leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  
                  {msg.role === "assistant" && (msg.confidence || msg.nodes) && (
                    <div className="mt-6 pt-5 border-t border-[var(--app-border)] flex items-center gap-6">
                      {msg.confidence && (
                        <Tooltip title="AI Confidence Score">
                          <span className="flex items-center gap-2 text-[10px] font-black text-emerald-500 uppercase tracking-widest bg-emerald-500/10 px-3 py-1 rounded-full">
                            <MdBarChart className="text-xs" /> {msg.confidence}%
                          </span>
                        </Tooltip>
                      )}
                      {msg.nodes && (
                        <Tooltip title="Knowledge Base Nodes Traversed">
                          <span className="flex items-center gap-2 text-[10px] font-black text-blue-500 uppercase tracking-widest bg-blue-500/10 px-3 py-1 rounded-full">
                            <PiGraphLight className="text-xs" /> {msg.nodes} Nodes
                          </span>
                        </Tooltip>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </Flex>
          ))}

          {isTyping && (
            <Flex justify="flex-start" className="animate-in fade-in duration-700">
              <div className="flex flex-col gap-2">
                <Flex align="center" gap={8} className="mb-1">
                  <Avatar icon={<LuBot />} className="bg-[#285d91]" />
                  <Text className="text-[10px] font-black uppercase tracking-widest text-[var(--app-text-soft)] italic">Thinking...</Text>
                </Flex>
                <div className="p-6 bg-[var(--app-surface)] border border-[var(--app-border)] text-[var(--app-text)] rounded-[32px] rounded-tl-none shadow-sm">
                  <p className="text-sm font-semibold leading-relaxed opacity-60">
                    {streamingText || "Synthesizing response from knowledge graph..."}
                  </p>
                </div>
              </div>
            </Flex>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input Dock */}
        <div className="px-10 py-10 bg-gradient-to-t from-[var(--app-surface)] to-transparent border-t border-[var(--app-border)]/50">
          <Flex vertical gap={12}>
            <div className="relative group/input">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={agent ? `Query ${agent.name}...` : "Synchronize with an architect..."}
                disabled={!agent || wsStatus !== "open"}
                className="!h-20 !pl-8 !pr-24 !bg-[var(--app-surface)] !border-[var(--app-border)] !rounded-[24px] !font-bold !text-lg !text-[var(--app-text)] !placeholder:text-[var(--app-text-soft)] focus:!ring-4 focus:!ring-[#285d91]/5 focus:!border-[#285d91]/20 !transition-all !shadow-2xl shadow-slate-200/10"
              />
              <button
                onClick={handleSend}
                disabled={!agent || !input.trim() || wsStatus !== "open"}
                className="absolute right-4 top-4 w-12 h-12 bg-[#285d91] text-white rounded-2xl flex items-center justify-center hover:scale-105 active:scale-95 disabled:opacity-20 disabled:hover:scale-100 transition-all shadow-xl shadow-blue-900/20"
              >
                <FiSend size={24} />
              </button>
            </div>
            <Flex justify="center" align="center" gap={16} className="mt-2">
              <span className="text-[9px] font-black uppercase tracking-[0.3em] text-[var(--app-text-soft)] hover:text-[#285d91] transition-colors cursor-pointer">Markdown Supported</span>
              <div className="w-1 h-1 bg-[var(--app-border)] rounded-full" />
              <span className="text-[9px] font-black uppercase tracking-[0.3em] text-[var(--app-text-soft)] hover:text-[#285d91] transition-colors cursor-pointer">Knowledge Base Context Active</span>
            </Flex>
          </Flex>
        </div>
      </Flex>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--app-border);
          border-radius: 20px;
          border: 2px solid transparent;
          background-clip: content-box;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: var(--app-text-soft);
          background-clip: content-box;
        }
      `}</style>
    </div>
  );
}