"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Button, Empty, Input, Spin } from "antd";
import { ReloadOutlined, ZoomInOutlined } from "@ant-design/icons";
import dynamic from "next/dynamic";
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });
import AgentList from "../../components/ui/AgentList";
import type { Agent } from "../../components/ui/type";
import useAxios from "../../hooks/useAxios";
import { useStore } from "../../hooks/useStore";

type NodeType = "Agent" | "KnowledgeBase" | "Chunk" | "Entity";

type RawNode = {
  id: string;
  type?: string;
  label?: string;
  properties?: Record<string, unknown>;
};

type RawEdge = {
  source: string;
  target: string;
  from?: string;
  to?: string;
  type?: string;
  properties?: Record<string, unknown>;
};

type GraphPayload = {
  nodes?: RawNode[];
  edges?: RawEdge[];
};

type GraphResponse = {
  data?: GraphPayload;
  nodes?: RawNode[];
  edges?: RawEdge[];
};

type AgentListResponse = {
  data?: {
    agents?: Agent[];
  };
};

type GraphNode = {
  id: string;
  type: NodeType;
  label: string;
  val: number;
  color: string;
  properties: Record<string, unknown>;
  x?: number;
  y?: number;
  fx?: number;
  fy?: number;
};

type GraphLink = {
  source: string | GraphNode;
  target: string | GraphNode;
  label: string;
  type: string;
};

type ForceGraph2DProps = Parameters<typeof ForceGraph2D<GraphNode, GraphLink>>[0];
type ForceGraph2DRef = NonNullable<ForceGraph2DProps["ref"]> extends React.MutableRefObject<infer Instance>
  ? Instance
  : never;

const NODE_COLORS: Record<NodeType, string> = {
  Agent: "#6366f1", // Indigo
  KnowledgeBase: "#06b6d4", // Cyan
  Chunk: "#8b5cf6", // Purple
  Entity: "#f59e0b", // Amber
};

const ENTITY_SUB_COLORS: Record<string, string> = {
  PERSON: "#ec4899",
  ORGANIZATION: "#f97316",
  CONCEPT: "#a855f7",
  LOCATION: "#22c55e",
};

function getEntityColor(node: RawNode): string {
  const subType = String(node.properties?.type ?? "");
  return ENTITY_SUB_COLORS[subType] || NODE_COLORS.Entity;
}

const NODE_STROKES: Record<NodeType, string> = {
  Agent: "#4f46e5",
  KnowledgeBase: "#0891b2",
  Chunk: "#7c3aed",
  Entity: "#d97706",
};

const NODE_VALUES: Record<NodeType, number> = {
  Agent: 12,
  KnowledgeBase: 8,
  Chunk: 5,
  Entity: 3,
};

const NODE_TYPES = Object.keys(NODE_COLORS) as NodeType[];

function normalizeType(type?: string): NodeType {
  if (type === "Agent" || type === "KnowledgeBase" || type === "Chunk" || type === "Entity") {
    return type;
  }
  return "Entity";
}

function getNodeLabel(node: RawNode) {
  const properties = node.properties ?? {};
  const possibleName = properties.name ?? properties.title ?? properties.text ?? node.label ?? node.id;
  return String(possibleName);
}

function getGraphPayload(response?: GraphResponse): GraphPayload {
  if (response?.data?.nodes || response?.data?.edges) return response.data;
  return { nodes: response?.nodes, edges: response?.edges };
}

function toGraphData(response?: GraphResponse) {
  const payload = getGraphPayload(response);
  const apiNodes = payload.nodes ?? [];
  const apiEdges = payload.edges ?? [];
  const nodeIds = new Set(apiNodes.map((node) => node.id));

  return {
    nodes: apiNodes.map((node): GraphNode => {
      const type = normalizeType(node.type);
      const color = type === "Entity" ? getEntityColor(node) : NODE_COLORS[type];
      // Filter out embedding arrays from properties
      const rawProps = node.properties ?? {};
      const filteredProps: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(rawProps)) {
        if (k === "embedding" || (Array.isArray(v) && v.length > 10)) continue;
        filteredProps[k] = v;
      }
      return {
        id: String(node.id),
        type,
        label: getNodeLabel(node),
        val: NODE_VALUES[type],
        color,
        properties: filteredProps,
      };
    }),
    links: (() => {
      const linksMap = new Map<string, GraphLink>();

      // 1. Add edges from API
      apiEdges.forEach((edge) => {
        const src = String(edge.source ?? edge.from ?? "");
        const tgt = String(edge.target ?? edge.to ?? "");
        if (nodeIds.has(src) && nodeIds.has(tgt)) {
          const type = String(edge.type ?? "RELATED_TO");
          linksMap.set(`${src}-${tgt}-${type}`, { source: src, target: tgt, label: type, type });
        }
      });

      // 2. Artificially infer and add Agent -> KB -> Chunk connections if missing
      const agents = apiNodes.filter((n) => normalizeType(n.type) === "Agent");
      const kbs = apiNodes.filter((n) => normalizeType(n.type) === "KnowledgeBase");
      const chunks = apiNodes.filter((n) => normalizeType(n.type) === "Chunk");

      // Agent -> KB
      if (agents.length > 0 && kbs.length > 0) {
        const primaryAgent = agents[0];
        kbs.forEach((kb) => {
          const key = `${primaryAgent.id}-${kb.id}-OWNS_KB`;
          if (!linksMap.has(key)) {
            linksMap.set(key, { source: primaryAgent.id, target: kb.id, label: "OWNS_KB", type: "OWNS_KB" });
          }
        });
      }

      // KB -> Chunk
      if (kbs.length > 0 && chunks.length > 0) {
        chunks.forEach((chunk) => {
          // Try to match KB by property if possible, else fallback to first KB
          const props = chunk.properties || {};
          const kbId = props.knowledge_base_id ?? props.kb_id ?? props.document_id;
          let targetKb = kbs.find((k) => k.id === kbId || k.properties?.document_id === kbId || k.properties?.id === kbId);
          if (!targetKb) targetKb = kbs[0]; // fallback

          const key = `${targetKb.id}-${chunk.id}-HAS_CHUNK`;
          if (!linksMap.has(key)) {
            linksMap.set(key, { source: targetKb.id, target: chunk.id, label: "HAS_CHUNK", type: "HAS_CHUNK" });
          }
        });
      }

      return Array.from(linksMap.values());
    })(),
  };
}

function mapAgentsToList(agents: Agent[]) {
  return agents.map((agent) => ({
    id: agent.id,
    name: agent.name,
    status: agent.is_active ? "active" : "draft",
  }));
}

function truncate(value: string, max = 72) {
  return value.length > max ? `${value.slice(0, max - 1)}...` : value;
}

function getLinkedNodeId(link: GraphLink, selectedId: string) {
  const sourceId = getEndpointId(link.source);
  const targetId = getEndpointId(link.target);
  if (sourceId !== selectedId) return sourceId;
  if (targetId !== selectedId) return targetId;
  return "";
}

function getEndpointId(endpoint: string | GraphNode) {
  return typeof endpoint === "string" ? endpoint : endpoint.id;
}

export default function GraphViewPage() {
  const requestedAgentsRef = useRef(false);
  const loadedGraphForRef = useRef("");
  const graphRef = useRef<ForceGraph2DRef>(undefined);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");

  const agentList = useStore((state) => state.agentList);
  const setAgentList = useStore((state) => state.setAgentList);
  const setBotsCache = useStore((state) => state.setBotsCache);

  const [getAgents] = useAxios<AgentListResponse>({ endpoint: "GETAGENTLIST", hideErrorMsg: true });
  const [getGraph, graphResponse, graphLoading] = useAxios<GraphResponse>({
    endpoint: "GRAPHVIEW",
    hideErrorMsg: false,
  });

  const activeAgentId = selectedAgentId || agentList[0]?.id || "";
  const activeAgentName = agentList.find((agent) => agent.id === activeAgentId)?.name ?? "Selected Agent";

  const graphData = useMemo(() => toGraphData(graphResponse), [graphResponse]);

  const nodeById = useMemo(() => {
    return new Map(graphData.nodes.map((node) => [node.id, node]));
  }, [graphData.nodes]);

  const filteredNodes = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return graphData.nodes;
    return graphData.nodes.filter((node) => {
      const properties = Object.values(node.properties).join(" ").toLowerCase();
      return `${node.label} ${node.type} ${properties}`.toLowerCase().includes(term);
    });
  }, [graphData.nodes, search]);

  const visibleNodeIds = useMemo(() => new Set(filteredNodes.map((node) => node.id)), [filteredNodes]);

  const visibleGraphData = useMemo(() => {
    return {
      nodes: filteredNodes,
      links: graphData.links.filter((link) => visibleNodeIds.has(getEndpointId(link.source)) && visibleNodeIds.has(getEndpointId(link.target))),
    };
  }, [filteredNodes, graphData.links, visibleNodeIds]);

  const selectedLinks = useMemo(() => {
    if (!selectedNode) return [];
    return graphData.links.filter((link) => getEndpointId(link.source) === selectedNode.id || getEndpointId(link.target) === selectedNode.id);
  }, [graphData.links, selectedNode]);

  const loadAgents = useCallback(() => {
    if (requestedAgentsRef.current || agentList.length > 0) return;
    requestedAgentsRef.current = true;
    getAgents(undefined, (payload) => {
      const agents = payload?.data?.agents ?? [];
      setBotsCache(agents);
      setAgentList(mapAgentsToList(agents));
    });
  }, [agentList.length, getAgents, setAgentList, setBotsCache]);

  const loadGraph = useCallback(
    (agentId: string, force = false) => {
      if (!agentId) return;
      if (!force && loadedGraphForRef.current === agentId) return;
      loadedGraphForRef.current = agentId;
      setSelectedNode(null);
      getGraph({ path: `/${agentId}` });
    },
    [getGraph],
  );

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  useEffect(() => {
    loadGraph(activeAgentId);
  }, [activeAgentId, loadGraph]);

  useEffect(() => {
    if (!graphData.nodes.length) return;
    
    if (graphRef.current) {
      // Increase repulsion between nodes to give entities more space
      graphRef.current.d3Force("charge")?.strength(-600)?.distanceMax(1000);
      // Increase default link distance
      graphRef.current.d3Force("link")?.distance(140);
    }
    
    window.setTimeout(() => graphRef.current?.zoomToFit(450, 70), 80);
  }, [graphData.nodes.length]);

  const handleRefresh = () => {
    loadedGraphForRef.current = "";
    loadGraph(activeAgentId, true);
    graphRef.current?.d3ReheatSimulation();
  };

  const handleFit = () => {
    graphRef.current?.zoomToFit(450, 70);
  };

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", gap: 18 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, color: "var(--app-text)", fontWeight: 700, fontSize: 38, lineHeight: 1.1 }}>
            Graph View
          </h1>
          <p style={{ margin: "8px 0 0", color: "var(--app-text-muted)", fontSize: 16 }}>
            {activeAgentId ? activeAgentName : "Select an agent to render its knowledge graph"}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <AgentList
            selectedId={activeAgentId || undefined}
            onChange={(id) => {
              setSelectedAgentId(id);
              loadedGraphForRef.current = "";
            }}
          />
          <Button icon={<ZoomInOutlined />} onClick={handleFit} disabled={!graphData.nodes.length} />
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={graphLoading} disabled={!activeAgentId} />
        </div>
      </div>

      <div
        style={{
          border: "1px solid #e2e8f0",
          background: "#ffffff",
          borderRadius: 12,
          overflow: "hidden",
          minHeight: 700,
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) 340px",
          boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
        }}
      >
        <div style={{ minWidth: 0, display: "flex", flexDirection: "column", background: "#ffffff" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              minHeight: 52,
              padding: "10px 16px",
              borderBottom: "1px solid #e2e8f0",
              background: "#ffffff",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: "#22c55e", boxShadow: "0 0 12px #22c55e" }} />
              <span style={{ color: "#64748b", fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>KNOWLEDGE GRAPH</span>
              <span style={{ color: "#4f46e5", fontSize: 11, fontWeight: 600 }}>
                {graphData.nodes.length} nodes · {graphData.links.length} relationships
              </span>
            </div>
            <Input.Search
              allowClear
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search graph"
              style={{ width: 240 }}
            />
          </div>

          <div style={{ position: "relative", height: 640, background: "#ffffff" }}>
            <div
              style={{
                position: "absolute",
                inset: 0,
                pointerEvents: "none",
                backgroundImage: "radial-gradient(circle, #e2e8f0 1px, transparent 1px)",
                backgroundSize: "28px 28px",
                opacity: 0.8,
              }}
            />

            {graphLoading && (
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "rgba(255,255,255,0.7)",
                  zIndex: 2,
                }}
              >
                <Spin size="large" />
              </div>
            )}

            {!activeAgentId && !graphLoading ? (
              <div style={{ position: "relative", zIndex: 1, height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Empty description="No agent selected" />
              </div>
            ) : graphData.nodes.length === 0 && !graphLoading ? (
              <div style={{ position: "relative", zIndex: 1, height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Empty description="No graph data found" />
              </div>
            ) : (
              <ForceGraph2D
                ref={graphRef}
                graphData={visibleGraphData}
                width={1000}
                height={640}
                backgroundColor="white"
                d3AlphaDecay={0.02}
                d3VelocityDecay={0.3}
                cooldownTicks={100}
                nodeId="id"
                nodeVal="val"
                nodeRelSize={6}
                nodeColor={(node) => node.color}
                nodeLabel={(node) => {
                  const title = `${node.type}: ${node.label}`;
                  const text = String(node.properties.text ?? node.properties.description ?? "");
                  return text ? `${title}\n${truncate(text, 160)}` : title;
                }}
                linkLabel={(link) => link.label}
                linkColor={(link) =>
                  selectedNode &&
                  (getEndpointId(link.source) === selectedNode.id || getEndpointId(link.target) === selectedNode.id)
                    ? "rgba(0, 0, 0, 0.8)"
                    : "rgba(0, 0, 0, 0.3)"
                }
                linkWidth={(link) =>
                  selectedNode &&
                  (getEndpointId(link.source) === selectedNode.id || getEndpointId(link.target) === selectedNode.id)
                    ? 2
                    : 1
                }
                linkCurvature={0}
                linkDirectionalArrowLength={6}
                linkDirectionalArrowRelPos={1}
                linkDirectionalParticles={(link) =>
                  selectedNode &&
                  (getEndpointId(link.source) === selectedNode.id || getEndpointId(link.target) === selectedNode.id)
                    ? 2
                    : 0
                }
                linkDirectionalParticleWidth={2}
                linkDirectionalParticleColor={() => "#000000"}
                linkDirectionalParticleSpeed={0.006}
                linkCanvasObjectMode={() => "after"}
                linkCanvasObject={(link, ctx, globalScale) => {
                  if (globalScale < 1.5) return; // Hide labels when zoomed out

                  const MAX_FONT_SIZE = 3.5;
                  const label = link.label;
                  const fontSize = Math.min(MAX_FONT_SIZE, 10 / globalScale);
                  ctx.font = `${fontSize}px Inter, system-ui, sans-serif`;

                  const start = typeof link.source === "string" ? { x: 0, y: 0 } : link.source;
                  const end = typeof link.target === "string" ? { x: 0, y: 0 } : link.target;

                  if (typeof start === "string" || typeof end === "string") return;

                  // Calculate label position (midpoint)
                  const textPos = {
                    x: start.x! + (end.x! - start.x!) / 2,
                    y: start.y! + (end.y! - start.y!) / 2,
                  };

                  const relAngle = Math.atan2(end.y! - start.y!, end.x! - start.x!);
                  const labelRotation = relAngle > Math.PI / 2 || relAngle < -Math.PI / 2 ? relAngle + Math.PI : relAngle;

                  ctx.save();
                  ctx.translate(textPos.x, textPos.y);
                  ctx.rotate(labelRotation);

                  const textWidth = ctx.measureText(label).width;
                  const bckgDimensions = [textWidth, fontSize].map((n) => n + fontSize * 0.5);

                  // Draw text background
                  ctx.fillStyle = "rgba(255, 255, 255, 0.85)";
                  ctx.beginPath();
                  const rx = bckgDimensions[0] / 2, ry = bckgDimensions[1] / 2;
                  ctx.roundRect(-rx, -ry, bckgDimensions[0], bckgDimensions[1], 3);
                  ctx.fill();

                  // Draw text
                  ctx.textAlign = "center";
                  ctx.textBaseline = "middle";
                  ctx.fillStyle = "#000000";
                  ctx.fillText(label, 0, 0);
                  ctx.restore();
                }}
                onNodeClick={(node) => setSelectedNode(node)}
                onBackgroundClick={() => setSelectedNode(null)}
                onNodeDragEnd={(node) => {
                  node.fx = node.x;
                  node.fy = node.y;
                }}
                nodeCanvasObject={(node, ctx, globalScale) => {
                  const typeRadius: Record<string, number> = { Agent: 24, KnowledgeBase: 20, Chunk: 14, Entity: 16 };
                  const radius = typeRadius[node.type] ?? 16;
                  const isSelected = selectedNode?.id === node.id;
                  const isConnected = selectedNode && graphData.links.some(
                    (l) => (getEndpointId(l.source) === selectedNode.id || getEndpointId(l.target) === selectedNode.id) &&
                           (getEndpointId(l.source) === node.id || getEndpointId(l.target) === node.id)
                  );
                  const fontSize = Math.max(3, 10 / globalScale);
                  const label = truncate(node.label, node.type === "Chunk" ? 16 : 14);
                  const dimmed = selectedNode && !isSelected && !isConnected;

                  // Glow for selected
                  if (isSelected) {
                    ctx.beginPath();
                    ctx.arc(node.x ?? 0, node.y ?? 0, radius + 6, 0, 2 * Math.PI);
                    ctx.fillStyle = node.color + "30";
                    ctx.fill();
                  }

                  // Main circle (Solid color for a cleaner look)
                  ctx.beginPath();
                  ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, 2 * Math.PI);
                  ctx.fillStyle = node.color + (dimmed ? "40" : "cc");
                  ctx.fill();

                  // Border ring
                  ctx.lineWidth = isSelected ? 3 : 1;
                  ctx.strokeStyle = isSelected ? "#000000" : (node.color + (dimmed ? "20" : "88"));
                  ctx.stroke();

                  // Label inside node
                  ctx.font = `${isSelected ? "bold " : ""}${fontSize}px Inter, system-ui, sans-serif`;
                  ctx.textAlign = "center";
                  ctx.textBaseline = "middle";
                  ctx.fillStyle = dimmed ? "rgba(0,0,0,0.3)" : "#000000";
                  
                  if (label.length > 10) {
                    const mid = Math.floor(label.length / 2);
                    const splitPos = label.indexOf(" ", mid - 3) > -1 ? label.indexOf(" ", mid - 3) : mid;
                    ctx.fillText(label.slice(0, splitPos), node.x ?? 0, (node.y ?? 0) - fontSize * 0.55);
                    ctx.fillText(label.slice(splitPos).trim(), node.x ?? 0, (node.y ?? 0) + fontSize * 0.55);
                  } else {
                    ctx.fillText(label, node.x ?? 0, node.y ?? 0);
                  }
                }}
              />
            )}
          </div>
        </div>

        <aside style={{ borderLeft: "1px solid #e2e8f0", background: "#f8fafc", padding: 18, color: "#334155", minWidth: 0, overflowY: "auto", maxHeight: 700 }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
            {NODE_TYPES.map((type) => (
              <span
                key={type}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  color: NODE_COLORS[type],
                  border: `1px solid ${NODE_COLORS[type]}55`,
                  background: `${NODE_COLORS[type]}18`,
                  borderRadius: 999,
                  padding: "4px 8px",
                  fontSize: 11,
                }}
              >
                <span style={{ width: 7, height: 7, borderRadius: 999, background: NODE_COLORS[type] }} />
                {type}
              </span>
            ))}
          </div>

          {selectedNode ? (
            <div>
              <div style={{ color: selectedNode.color, fontSize: 12, fontWeight: 700, marginBottom: 6 }}>{selectedNode.type}</div>
              <h2 style={{ margin: "0 0 14px", color: "#0f172a", fontSize: 20, lineHeight: 1.25 }}>{selectedNode.label}</h2>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {Object.entries(selectedNode.properties).map(([key, value]) => (
                  <div key={key}>
                    <div style={{ color: "#64748b", fontSize: 11, marginBottom: 3, textTransform: "uppercase", letterSpacing: 0.5 }}>{key}</div>
                    <div style={{ color: "#334155", fontSize: 12, lineHeight: 1.45, overflowWrap: "anywhere" }}>
                      {String(value)}
                    </div>
                  </div>
                ))}
              </div>

              {selectedLinks.length > 0 && (
                <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid #e2e8f0" }}>
                  <div style={{ color: "#64748b", fontSize: 11, marginBottom: 8, letterSpacing: 1 }}>RELATIONSHIPS</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {selectedLinks.map((link, index) => {
                      const otherNode = nodeById.get(getLinkedNodeId(link, selectedNode.id));
                      return (
                        <div key={`${getEndpointId(link.source)}-${getEndpointId(link.target)}-${index}`} style={{ fontSize: 12, lineHeight: 1.35 }}>
                          <span style={{ color: "#4f46e5", fontWeight: 600 }}>{link.label}</span>
                          <span style={{ color: "#94a3b8" }}>{" -> "}</span>
                          <span style={{ color: "#334155", fontWeight: 500 }}>{otherNode?.label ?? "Unknown"}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ color: "#64748b", fontSize: 13, lineHeight: 1.5 }}>
              Select a node to inspect its properties and connected relationships.
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
