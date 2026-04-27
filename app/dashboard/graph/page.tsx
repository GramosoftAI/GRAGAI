"use client"
import { useEffect, useRef, useState, useCallback } from "react";
import type { MouseEvent, WheelEvent } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
type NodeType = "Agent" | "KnowledgeBase" | "Chunk" | "Entity";

interface RawNode {
  id: string;
  type: NodeType;
  properties: Record<string, string>;
}

interface RawEdge {
  from: string;
  to: string;
  type: string;
}

interface SimNode extends RawNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

interface SimLink {
  from: string;
  to: string;
  type: string;
  source: SimNode;
  target: SimNode;
}

interface Transform {
  scale: number;
  ox: number;
  oy: number;
}

interface TooltipState {
  x: number;
  y: number;
  node: SimNode;
}

interface ApiResponse {
  data: {
    nodes: RawNode[];
    edges: RawEdge[];
  };
}

interface Props {
  apiResponse?: ApiResponse;
}

// ─── Config ───────────────────────────────────────────────────────────────────
const NODE_COLORS: Record<NodeType, { fill: string; stroke: string; glow: string; label: string }> = {
  Agent:         { fill: "#FFD700", stroke: "#B8860B", glow: "#FFD70066", label: "#7A5800" },
  KnowledgeBase: { fill: "#4CAF50", stroke: "#2E7D32", glow: "#4CAF5066", label: "#1B5E20" },
  Chunk:         { fill: "#2196F3", stroke: "#0D47A1", glow: "#2196F366", label: "#0D47A1" },
  Entity:        { fill: "#9C27B0", stroke: "#6A1B9A", glow: "#9C27B066", label: "#6A1B9A" },
};

const NODE_RADIUS: Record<NodeType, number> = {
  Agent: 28,
  KnowledgeBase: 20,
  Chunk: 14,
  Entity: 10,
};

// ─── Force Simulation ─────────────────────────────────────────────────────────
function useForce(
  rawNodes: RawNode[],
  rawEdges: RawEdge[],
  width: number,
  height: number,
) {
  const nodesRef = useRef<SimNode[]>([]);
  const linksRef = useRef<SimLink[]>([]);
  const initialized = useRef(false);

  if (!initialized.current && rawNodes.length) {
    const cx = width / 2;
    const cy = height / 2;

    nodesRef.current = rawNodes.map((n: RawNode, i: number): SimNode => {
      const angle = (i / rawNodes.length) * Math.PI * 2;
      const radius =
        n.type === "Agent" ? 0
        : n.type === "KnowledgeBase" ? 100
        : n.type === "Chunk" ? 200
        : 300;
      return {
        ...n,
        x: cx + Math.cos(angle) * radius + (Math.random() - 0.5) * 40,
        y: cy + Math.sin(angle) * radius + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
        r: NODE_RADIUS[n.type] ?? 12,
      };
    });

    const nodeMap = new Map<string, SimNode>(
      nodesRef.current.map((n) => [n.id, n])
    );

    linksRef.current = rawEdges
      .map((e: RawEdge): SimLink | null => {
        const source = nodeMap.get(e.from);
        const target = nodeMap.get(e.to);
        if (!source || !target) return null;
        return { ...e, source, target };
      })
      .filter((l): l is SimLink => l !== null);

    initialized.current = true;
  }

  const tick = useCallback(
    (pinnedId: string | null) => {
      const alpha = 0.05;
      const nodes = nodesRef.current;
      const links = linksRef.current;
      const cx = width / 2;
      const cy = height / 2;

      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i];
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = 3200 / (d * d);
          const fx = (dx / d) * force * alpha;
          const fy = (dy / d) * force * alpha;
          a.vx += fx; a.vy += fy;
          b.vx -= fx; b.vy -= fy;
        }
      }

      links.forEach((l) => {
        const dx = l.target.x - l.source.x;
        const dy = l.target.y - l.source.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const ideal = (l.source.r + l.target.r) * 4 + 50;
        const stretch = (d - ideal) * 0.04 * alpha;
        const fx = (dx / d) * stretch;
        const fy = (dy / d) * stretch;
        if (l.source.id !== pinnedId) { l.source.vx += fx; l.source.vy += fy; }
        if (l.target.id !== pinnedId) { l.target.vx += fx; l.target.vy += fy; }
      });

      nodes.forEach((n) => {
        if (n.id === pinnedId) { n.vx = 0; n.vy = 0; return; }
        n.vx += (cx - n.x) * 0.004 * alpha;
        n.vy += (cy - n.y) * 0.004 * alpha;
        n.vx *= 0.80;
        n.vy *= 0.80;
        n.x += n.vx;
        n.y += n.vy;
      });
    },
    [width, height],
  );

  return { nodesRef, linksRef, tick };
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function KnowledgeGraph({ apiResponse }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const [selected, setSelected] = useState<SimNode | null>(null);
  const [hovered, setHovered] = useState<SimNode | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const draggingRef = useRef<SimNode | null>(null);
  const panRef = useRef<{ sx: number; sy: number } | null>(null);
  const transformRef = useRef<Transform>({ scale: 1, ox: 0, oy: 0 });
  const dragStartRef = useRef({ x: 0, y: 0 });

  const WIDTH = 800;
  const HEIGHT = 520;

  const rawNodes: RawNode[] = apiResponse?.data?.nodes ?? DEMO_DATA.nodes;
  const rawEdges: RawEdge[] = apiResponse?.data?.edges ?? DEMO_DATA.edges;

  const { nodesRef, linksRef, tick } = useForce(rawNodes, rawEdges, WIDTH, HEIGHT);

  const toWorld = (ex: number, ey: number): [number, number] => {
    const { scale, ox, oy } = transformRef.current;
    return [(ex / scale) - ox, (ey / scale) - oy];
  };

  const getNodeAt = (ex: number, ey: number): SimNode | null => {
    const [wx, wy] = toWorld(ex, ey);
    for (let i = nodesRef.current.length - 1; i >= 0; i--) {
      const n = nodesRef.current[i];
      if (Math.hypot(n.x - wx, n.y - wy) <= n.r + 6) return n;
    }
    return null;
  };

  // ─── Draw loop ───────────────────────────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    const draw = () => {
      ctx.clearRect(0, 0, WIDTH, HEIGHT);
      const { scale, ox, oy } = transformRef.current;
      ctx.save();
      ctx.scale(scale, scale);
      ctx.translate(ox, oy);

      const nodes = nodesRef.current;
      const links = linksRef.current;
      const sel = selected;
      const hov = hovered;

      links.forEach((l) => {
        const active = sel !== null && (l.source.id === sel.id || l.target.id === sel.id);
        ctx.save();
        ctx.globalAlpha = active ? 0.95 : 0.35;
        ctx.beginPath();
        ctx.moveTo(l.source.x, l.source.y);
        ctx.lineTo(l.target.x, l.target.y);
        ctx.strokeStyle = active ? "#FFD700" : (dark ? "#666" : "#bbb");
        ctx.lineWidth = active ? 1.8 : 0.8;
        ctx.stroke();

        const dx = l.target.x - l.source.x;
        const dy = l.target.y - l.source.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        const ux = dx / len;
        const uy = dy / len;
        const ax = l.target.x - ux * (l.target.r + 4);
        const ay = l.target.y - uy * (l.target.r + 4);
        ctx.beginPath();
        ctx.moveTo(ax - uy * 4 - ux * 8, ay + ux * 4 - uy * 8);
        ctx.lineTo(ax, ay);
        ctx.lineTo(ax + uy * 4 - ux * 8, ay - ux * 4 - uy * 8);
        ctx.strokeStyle = active ? "#FFD700" : (dark ? "#666" : "#bbb");
        ctx.lineWidth = active ? 1.5 : 0.8;
        ctx.stroke();

        if (active) {
          const mx = (l.source.x + l.target.x) / 2;
          const my = (l.source.y + l.target.y) / 2;
          ctx.font = "9px 'JetBrains Mono', monospace";
          ctx.fillStyle = dark ? "#aaa" : "#888";
          ctx.textAlign = "center";
          ctx.globalAlpha = 0.85;
          ctx.fillText(l.type, mx, my - 5);
        }
        ctx.restore();
      });

      nodes.forEach((n) => {
        const c = NODE_COLORS[n.type];
        const isSel = sel !== null && n.id === sel.id;
        const isHov = hov !== null && n.id === hov.id;
        const dimmed =
          sel !== null &&
          !isSel &&
          !links.some(
            (l) =>
              (l.source.id === sel.id && l.target.id === n.id) ||
              (l.target.id === sel.id && l.source.id === n.id),
          );

        ctx.save();
        ctx.globalAlpha = dimmed ? 0.2 : 1;

        if (isSel || isHov) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r + 10, 0, Math.PI * 2);
          ctx.fillStyle = c.glow;
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = c.fill;
        ctx.fill();
        ctx.strokeStyle = c.stroke;
        ctx.lineWidth = isSel ? 2.5 : 1;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(n.x - n.r * 0.3, n.y - n.r * 0.3, n.r * 0.35, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(255,255,255,0.25)";
        ctx.fill();

        const label = n.properties?.name ?? n.id;
        const maxLen = n.r > 18 ? 11 : 10;
        const short = label.length > maxLen ? label.slice(0, maxLen - 1) + "…" : label;
        ctx.font = `${n.r > 18 ? "10px" : "8px"} 'JetBrains Mono', monospace`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        if (n.r > 18) {
          ctx.fillStyle = c.label;
          ctx.fillText(short, n.x, n.y);
          ctx.font = "7px 'JetBrains Mono', monospace";
          ctx.globalAlpha *= 0.65;
          ctx.fillText(n.type.toUpperCase(), n.x, n.y + 11);
        } else {
          ctx.fillStyle = dark ? "#ccc" : "#444";
          ctx.fillText(short, n.x, n.y + n.r + 9);
        }

        ctx.restore();
      });

      ctx.restore();
    };

    const loop = () => {
      tick(draggingRef.current?.id ?? null);
      draw();
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [selected, hovered, tick]);

  // ─── Event handlers ───────────────────────────────────────────────────────────
  const onMouseDown = (e: MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const ex = e.clientX - rect.left;
    const ey = e.clientY - rect.top;
    const n = getNodeAt(ex, ey);
    if (n) {
      draggingRef.current = n;
      dragStartRef.current = { x: ex, y: ey };
    } else {
      panRef.current = {
        sx: ex - transformRef.current.ox * transformRef.current.scale,
        sy: ey - transformRef.current.oy * transformRef.current.scale,
      };
    }
  };

  const onMouseMove = (e: MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const ex = e.clientX - rect.left;
    const ey = e.clientY - rect.top;

    if (draggingRef.current) {
      const [wx, wy] = toWorld(ex, ey);
      draggingRef.current.x = wx;
      draggingRef.current.y = wy;
      draggingRef.current.vx = 0;
      draggingRef.current.vy = 0;
    } else if (panRef.current) {
      const { scale } = transformRef.current;
      transformRef.current.ox = (ex - panRef.current.sx) / scale;
      transformRef.current.oy = (ey - panRef.current.sy) / scale;
    }

    const n = getNodeAt(ex, ey);
    setHovered(n);
    setTooltip(n ? { x: ex + 14, y: ey - 8, node: n } : null);
    canvasRef.current!.style.cursor = n ? "pointer" : panRef.current ? "grabbing" : "grab";
  };

  const onMouseUp = (e: MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const ex = e.clientX - rect.left;
    const ey = e.clientY - rect.top;
    const dist = Math.hypot(ex - dragStartRef.current.x, ey - dragStartRef.current.y);
    if (draggingRef.current && dist < 5) {
      const n = draggingRef.current;
      setSelected((prev) => (prev?.id === n.id ? null : n));
    }
    draggingRef.current = null;
    panRef.current = null;
  };

  const onWheel = (e: WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const rect = canvasRef.current!.getBoundingClientRect();
    const ex = e.clientX - rect.left;
    const ey = e.clientY - rect.top;
    const { scale } = transformRef.current;
    const [wx, wy] = toWorld(ex, ey);
    const newScale = Math.max(0.25, Math.min(4, scale * (e.deltaY < 0 ? 1.12 : 0.9)));
    transformRef.current = { scale: newScale, ox: ex / newScale - wx, oy: ey / newScale - wy };
  };

  const connectedLinks = selected
    ? linksRef.current.filter(
        (l) => l.source.id === selected.id || l.target.id === selected.id,
      )
    : [];

  // ─── Render ───────────────────────────────────────────────────────────────────
  return (
    <div style={{ fontFamily: "'JetBrains Mono','Fira Code',monospace", background: "#0d0d0d", color: "#e0e0e0", borderRadius: 16, overflow: "hidden", border: "1px solid #2a2a2a" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 16px", borderBottom: "1px solid #2a2a2a", background: "#161616" }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#4CAF50", boxShadow: "0 0 8px #4CAF50" }} />
        <span style={{ fontSize: 11, color: "#666" }}>KNOWLEDGE GRAPH</span>
        <span style={{ fontSize: 11, color: "#FFD700", marginLeft: "auto" }}>
          {nodesRef.current.length} nodes · {linksRef.current.length} relationships
        </span>
        <div style={{ display: "flex", gap: 6 }}>
          {(Object.entries(NODE_COLORS) as [NodeType, typeof NODE_COLORS[NodeType]][]).map(([type, c]) => (
            <span key={type} style={{ fontSize: 9, padding: "2px 7px", borderRadius: 999, background: c.fill + "22", color: c.fill, border: `1px solid ${c.fill}44` }}>
              {type}
            </span>
          ))}
        </div>
      </div>

      {/* Canvas */}
      <div style={{ position: "relative", background: "#0a0a0a" }}>
        <div style={{ position: "absolute", inset: 0, pointerEvents: "none", backgroundImage: "radial-gradient(circle, #1a1a1a 1px, transparent 1px)", backgroundSize: "28px 28px", opacity: 0.6 }} />
        <canvas
          ref={canvasRef}
          width={WIDTH}
          height={HEIGHT}
          style={{ display: "block", width: "100%", cursor: "grab" }}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={onMouseUp}
          onMouseLeave={() => { setHovered(null); setTooltip(null); panRef.current = null; draggingRef.current = null; }}
          onWheel={onWheel}
        />

        {tooltip && (
          <div style={{ position: "absolute", left: Math.min(tooltip.x, WIDTH - 220), top: tooltip.y, background: "#1a1a1a", border: "1px solid #333", borderRadius: 8, padding: "8px 12px", fontSize: 11, pointerEvents: "none", maxWidth: 220, zIndex: 10 }}>
            <div style={{ color: NODE_COLORS[tooltip.node.type].fill, fontWeight: "bold", marginBottom: 4, fontSize: 10 }}>{tooltip.node.type}</div>
            {Object.entries(tooltip.node.properties ?? {}).map(([k, v]) => (
              <div key={k} style={{ marginBottom: 2 }}>
                <span style={{ color: "#666" }}>{k}: </span>
                <span style={{ color: "#ccc" }}>{String(v).slice(0, 60)}{String(v).length > 60 ? "…" : ""}</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ position: "absolute", bottom: 10, left: 12, fontSize: 9, color: "#444" }}>
          scroll to zoom · drag to pan · click to inspect
        </div>
      </div>

      {/* Detail panel */}
      <div style={{ padding: "10px 16px", borderTop: "1px solid #2a2a2a", background: "#161616", minHeight: 52, fontSize: 11 }}>
        {selected ? (
          <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div>
              <span style={{ color: NODE_COLORS[selected.type].fill, fontWeight: "bold" }}>[{selected.type}]</span>{" "}
              {Object.entries(selected.properties ?? {}).map(([k, v]) => (
                <span key={k} style={{ marginRight: 10 }}>
                  <span style={{ color: "#555" }}>{k}=</span>
                  <span style={{ color: "#ccc" }}>{String(v).slice(0, 50)}</span>
                </span>
              ))}
            </div>
            {connectedLinks.length > 0 && (
              <div style={{ color: "#555" }}>
                {connectedLinks.map((l, i) => {
                  const other = l.source.id === selected.id ? l.target : l.source;
                  const dir = l.source.id === selected.id ? "→" : "←";
                  return (
                    <span key={i} style={{ marginRight: 8 }}>
                      <span style={{ color: "#FFD700" }}>{dir} {l.type}</span>{" "}
                      <span style={{ color: NODE_COLORS[other.type].fill }}>{other.properties?.name ?? other.id}</span>
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        ) : (
          <span style={{ color: "#444" }}>Click any node to inspect properties and relationships</span>
        )}
      </div>
    </div>
  );
}

// ─── Demo data ────────────────────────────────────────────────────────────────
const DEMO_DATA: { nodes: RawNode[]; edges: RawEdge[] } = {
  nodes: [
    { id: "a1",  type: "Agent",         properties: { name: "SimplFin Bot",   personality: "Helpful finance assistant", system_prompt: "You help users understand SimplFin products." } },
    { id: "kb1", type: "KnowledgeBase", properties: { name: "simplfin.tech",  url: "https://simplfin.tech" } },
    { id: "kb2", type: "KnowledgeBase", properties: { name: "Product Docs",   url: "https://simplfin.tech/docs" } },
    { id: "c1",  type: "Chunk",         properties: { text: "SimplFin offers FLEXCUBE integration for retail banking." } },
    { id: "c2",  type: "Chunk",         properties: { text: "Oracle FLEXCUBE supports multi-currency transactions." } },
    { id: "c3",  type: "Chunk",         properties: { text: "Pricing starts at $499/month for small teams." } },
    { id: "c4",  type: "Chunk",         properties: { text: "API rate limits enforced via JWT-based middleware." } },
    { id: "e1",  type: "Entity",        properties: { name: "FLEXCUBE",       category: "Product" } },
    { id: "e2",  type: "Entity",        properties: { name: "Oracle",         category: "Company" } },
    { id: "e3",  type: "Entity",        properties: { name: "Southeast Asia", category: "Region" } },
    { id: "e4",  type: "Entity",        properties: { name: "$499/month",     category: "Pricing" } },
    { id: "e5",  type: "Entity",        properties: { name: "JWT",            category: "Technology" } },
    { id: "e6",  type: "Entity",        properties: { name: "Multi-currency", category: "Feature" } },
  ],
  edges: [
    { from: "a1",  to: "kb1", type: "HAS_KNOWLEDGE" },
    { from: "a1",  to: "kb2", type: "HAS_KNOWLEDGE" },
    { from: "kb1", to: "c1",  type: "HAS_CHUNK" },
    { from: "kb1", to: "c2",  type: "HAS_CHUNK" },
    { from: "kb2", to: "c3",  type: "HAS_CHUNK" },
    { from: "kb2", to: "c4",  type: "HAS_CHUNK" },
    { from: "c1",  to: "e1",  type: "CONTAINS_ENTITY" },
    { from: "c1",  to: "e3",  type: "CONTAINS_ENTITY" },
    { from: "c2",  to: "e1",  type: "CONTAINS_ENTITY" },
    { from: "c2",  to: "e2",  type: "CONTAINS_ENTITY" },
    { from: "c2",  to: "e6",  type: "CONTAINS_ENTITY" },
    { from: "c3",  to: "e4",  type: "CONTAINS_ENTITY" },
    { from: "c4",  to: "e5",  type: "CONTAINS_ENTITY" },
  ],
};