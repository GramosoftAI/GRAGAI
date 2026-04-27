"use client";

import { Flex, Typography } from "antd";
import React, { useState, useRef, useEffect } from "react";
import { LuBot } from "react-icons/lu";
import { FiUser, FiSend } from "react-icons/fi";
import { MdBarChart } from "react-icons/md";
import { PiGraphLight } from "react-icons/pi";
import { getCookie } from "../../config/cookies";
import AgentList from "../../components/ui/AgentList";

const { Text } = Typography;

type Message = {
  role: "user" | "assistant";
  content: string;
  confidence?: number;
  nodes?: number;
};

export default function ChatPlaygroundPage() {
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const ws = useRef<WebSocket | null>(null);
  const streamingTextRef = useRef<string>("");

  // ✅ Connect WebSocket
  useEffect(() => {
    if (!agent?.id) return;

    ws.current = new WebSocket(
      `ws://192.168.1.10:4915/api/v1/rag/ws/${agent.id}?token=${getCookie("AUTH_TOKEN")}`
    );

    ws.current.onopen = () => {
      console.log("✅ WebSocket Connected");
    };

    ws.current.onmessage = (event) => {
      console.log("WS RAW:", event.data);

      try {
        const data = JSON.parse(event.data);

        if (data.type === "metadata") return;

        if (data.type === "done") {
          const accumulated = streamingTextRef.current;
          if (accumulated) {
            setMessages((prev) => [
              ...prev,
              { role: "assistant", content: accumulated },
            ]);
          }
          streamingTextRef.current = "";
          setStreamingText("");
          setIsTyping(false);
          return;
        }

        if (data.type === "chunk" || data.type === "delta") {
          streamingTextRef.current += data.message || "";
          setStreamingText(streamingTextRef.current);
          setIsTyping(true);
          return;
        }

        if (data.message) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: data.message },
          ]);
          setIsTyping(false);
          return;
        }
      } catch {
        if (typeof event.data === "string" && event.data.startsWith("Error")) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: event.data },
          ]);
          streamingTextRef.current = "";
          setStreamingText("");
          setIsTyping(false);
          return;
        }

        streamingTextRef.current += event.data;
        setStreamingText(streamingTextRef.current);
        setIsTyping(true);
      }
    };

    ws.current.onerror = (err) => console.error("❌ WebSocket Error:", err);
    ws.current.onclose = () => console.log("🔌 WebSocket Closed");

    return () => {
      ws.current?.close();
    };
  }, [agent?.id]);

  // ✅ Auto scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // ✅ Send message
  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !agent?.id) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    streamingTextRef.current = "";
    setStreamingText("");
    setIsTyping(true);

    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ query: trimmed }));
    } else {
      console.error("WS not connected");
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSend();
  };

  return (
    <Flex gap={16} style={{ height: "calc(100vh - 120px)" }}>
      {/* Chat Panel */}
      <Flex
        vertical
        flex={1}
        style={{
          border: "1px solid #1f2d25",
          borderRadius: 12,
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <Flex
          justify="space-between"
          align="center"
          style={{
            padding: "16px 20px",
            borderBottom: "1px solid #1a2a20",
          }}
        >
          <h2 style={{ color: "#fff", fontWeight: 700, fontSize: 18, margin: 0 }}>
            Chat Playground
          </h2>
          <AgentList
            selectedId={agent?.id}
            onChange={(id: string, name: string) => setAgent({ id, name })}
          />
        </Flex>

        {/* Messages */}
        <Flex
          vertical
          flex={1}
          gap={16}
          style={{
            padding: "16px 20px",
            overflowY: "auto",
          }}
        >
          {messages.map((msg, i) =>
            msg.role === "user" ? (
              <Flex key={i} justify="flex-end">
                <div
                  style={{
                    background: "#0f3d2a",
                    border: "1px solid #1a5c3a",
                    borderRadius: 12,
                    padding: "10px 14px",
                    maxWidth: "60%",
                  }}
                >
                  <Flex align="center" gap={8} style={{ marginBottom: 4 }}>
                    <FiUser size={12} color="#22c55e" />
                    <Text style={{ fontSize: 12, color: "#22c55e" }}>User</Text>
                  </Flex>
                  <p style={{ color: "#fff", margin: 0 }}>{msg.content}</p>
                </div>
              </Flex>
            ) : (
              <Flex key={i} justify="flex-start">
                <div
                  style={{
                    background: "#111a14",
                    border: "1px solid #1f2d1f",
                    borderRadius: 12,
                    padding: "12px 16px",
                    maxWidth: "75%",
                  }}
                >
                  <Flex align="center" gap={8} style={{ marginBottom: 8 }}>
                    <LuBot size={12} color="#22c55e" />
                    <Text style={{ fontSize: 12, color: "#22c55e" }}>Assistant</Text>
                  </Flex>

                  <p style={{ color: "#e5e7eb", margin: 0 }}>{msg.content}</p>

                  {(msg.confidence !== undefined || msg.nodes !== undefined) && (
                    <Flex gap={16} style={{ marginTop: 12 }}>
                      {msg.confidence !== undefined && (
                        <Flex align="center" gap={4}>
                          <MdBarChart size={13} />
                          <Text style={{ fontSize: 12 }}>{msg.confidence}%</Text>
                        </Flex>
                      )}
                      {msg.nodes !== undefined && (
                        <Flex align="center" gap={4}>
                          <PiGraphLight size={13} />
                          <Text style={{ fontSize: 12 }}>{msg.nodes} nodes</Text>
                        </Flex>
                      )}
                    </Flex>
                  )}
                </div>
              </Flex>
            )
          )}

          {/* Streaming / Typing bubble */}
          {isTyping && (
            <Flex justify="flex-start">
              <div
                style={{
                  background: "#111a14",
                  border: "1px solid #1f2d1f",
                  borderRadius: 12,
                  padding: "12px 16px",
                  maxWidth: "75%",
                }}
              >
                <Flex align="center" gap={8} style={{ marginBottom: 8 }}>
                  <LuBot size={12} color="#22c55e" />
                  <Text style={{ fontSize: 12, color: "#22c55e" }}>Assistant</Text>
                </Flex>
                <p style={{ color: "#e5e7eb", margin: 0 }}>
                  {streamingText || "Typing..."}
                </p>
              </div>
            </Flex>
          )}

          <div ref={bottomRef} />
        </Flex>

        {/* Input */}
        <Flex
          gap={12}
          style={{
            padding: "12px 16px",
            borderTop: "1px solid #1a2a20",
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={agent ? "Ask something..." : "Select an agent first..."}
            disabled={!agent}
            style={{
              flex: 1,
              border: "1px solid #2d2d2d",
              padding: "10px",
              borderRadius: 8,
              background: "#0a110c",
              color: "#fff",
              opacity: agent ? 1 : 0.5,
              outline: "none",
            }}
          />
          <button
            onClick={handleSend}
            disabled={!agent || !input.trim()}
            style={{
              background: "transparent",
              border: "none",
              cursor: !agent || !input.trim() ? "not-allowed" : "pointer",
              opacity: !agent || !input.trim() ? 0.4 : 1,
              padding: 0,
              display: "flex",
              alignItems: "center",
            }}
          >
            <FiSend color="#22c55e" size={18} />
          </button>
        </Flex>
      </Flex>
    </Flex>
  );
}