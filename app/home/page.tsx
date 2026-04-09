"use client";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";

// ─── Animated Graph Canvas Background ───────────────────────────────────────
// ─── Mini demo graph (SVG) ───────────────────────────────────────────────────
function DemoGraph() {
  const nodes = [
    { id: "c", x: 260, y: 160, label: "Central Idea", main: true },
    { id: "a", x: 100, y: 60, label: "Research", main: false },
    { id: "b", x: 420, y: 55, label: "Strategy", main: false },
    { id: "d", x: 80, y: 270, label: "Design", main: false },
    { id: "e", x: 430, y: 265, label: "Execution", main: false },
    { id: "f", x: 255, y: 295, label: "Analytics", main: false },
    { id: "g", x: 155, y: 175, label: "Planning", main: false },
  ];
  const edges = [
    ["c", "a"], ["c", "b"], ["c", "d"], ["c", "e"], ["c", "f"], ["c", "g"],
    ["a", "g"], ["b", "e"],
  ];
  return (
    <svg viewBox="0 0 520 340" style={{ width: "100%", height: "auto" }}>
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge><feMergeNode in="coloredBlur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <radialGradient id="nodeGrad" cx="50%" cy="35%">
          <stop offset="0%" stopColor="#63d2be" />
          <stop offset="100%" stopColor="#1a6b5e" />
        </radialGradient>
        <radialGradient id="mainGrad" cx="50%" cy="35%">
          <stop offset="0%" stopColor="#ffe066" />
          <stop offset="100%" stopColor="#b88a00" />
        </radialGradient>
      </defs>
      {edges.map(([a, b], i) => {
        const na = nodes.find(n => n.id === a)!;
        const nb = nodes.find(n => n.id === b)!;
        return (
          <line key={i}
            x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
            stroke="#63d2be" strokeWidth="1.5" strokeOpacity="0.35"
            strokeDasharray="5 4"
          />
        );
      })}
      {nodes.map(n => (
        <g key={n.id} filter="url(#glow)">
          <circle
            cx={n.x} cy={n.y}
            r={n.main ? 30 : 22}
            fill={n.main ? "url(#mainGrad)" : "url(#nodeGrad)"}
            fillOpacity="0.92"
            stroke={n.main ? "#ffe066" : "#63d2be"}
            strokeWidth={n.main ? 2.5 : 1.5}
            strokeOpacity="0.8"
          />
          <text
            x={n.x} y={n.y + 1}
            textAnchor="middle" dominantBaseline="middle"
            fontSize={n.main ? 9.5 : 8}
            fontFamily="'Space Mono', monospace"
            fontWeight={n.main ? "700" : "400"}
            fill={n.main ? "#1a0f00" : "#e0fff8"}
          >
            {n.label}
          </text>
        </g>
      ))}
    </svg>
  );
}

// ─── Feature Card ─────────────────────────────────────────────────────────────
function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: hovered
          ? "linear-gradient(135deg,rgba(99,210,190,0.10) 0%,rgba(255,224,102,0.06) 100%)"
          : "rgba(10,24,22,0.7)",
        border: `1px solid ${hovered ? "rgba(99,210,190,0.4)" : "rgba(99,210,190,0.12)"}`,
        borderRadius: 16,
        padding: "28px 24px",
        backdropFilter: "blur(12px)",
        transition: "all 0.3s ease",
        transform: hovered ? "translateY(-4px)" : "translateY(0)",
        cursor: "default",
      }}
    >
      <div style={{ fontSize: 32, marginBottom: 14 }}>{icon}</div>
      <div style={{
        fontFamily: "'Space Mono', monospace",
        fontSize: 13,
        color: "#63d2be",
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        marginBottom: 8,
        fontWeight: 700,
      }}>{title}</div>
      <div style={{
        fontFamily: "'Lora', serif",
        fontSize: 14.5,
        color: "#8cbfb8",
        lineHeight: 1.7,
      }}>{desc}</div>
    </div>
  );
}

// ─── Stat ─────────────────────────────────────────────────────────────────────
function Stat({ n, label }: { n: string; label: string }) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{
        fontFamily: "'Space Mono', monospace",
        fontSize: 38,
        fontWeight: 700,
        color: "#ffe066",
        letterSpacing: "-0.02em",
        lineHeight: 1,
      }}>{n}</div>
      <div style={{
        fontFamily: "'Lora', serif",
        color: "#5a8880",
        fontSize: 13,
        marginTop: 6,
        letterSpacing: "0.05em",
      }}>{label}</div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function HomePage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const router = useRouter()
  return (
    <>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Lora:ital,wght@0,400;0,600;1,400&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { background: #060f0e; color: #d4f0eb; }
        ::selection { background: rgba(99,210,190,0.3); }

        @keyframes fadeUp {
          from { opacity:0; transform:translateY(28px); }
          to   { opacity:1; transform:translateY(0); }
        }
        @keyframes pulse-ring {
          0%,100% { box-shadow: 0 0 0 0 rgba(99,210,190,0.35); }
          50%      { box-shadow: 0 0 0 14px rgba(99,210,190,0); }
        }
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        .fade-up { animation: fadeUp 0.7s ease both; }
        .delay-1 { animation-delay: 0.12s; }
        .delay-2 { animation-delay: 0.24s; }
        .delay-3 { animation-delay: 0.38s; }
        .delay-4 { animation-delay: 0.52s; }

        .cta-btn {
          display:inline-flex; align-items:center; gap:8px;
          background: linear-gradient(135deg,#63d2be,#3db8a4);
          color:#060f0e; font-family:'Space Mono',monospace;
          font-size:13px; font-weight:700; letter-spacing:0.05em;
          padding:14px 30px; border-radius:999px; border:none;
          cursor:pointer; transition:all 0.25s ease;
          text-transform:uppercase; animation: pulse-ring 2.8s infinite;
        }
        .cta-btn:hover { transform:scale(1.05); background:linear-gradient(135deg,#8eeee0,#63d2be); }

        .outline-btn {
          display:inline-flex; align-items:center; gap:8px;
          background:transparent; color:#63d2be;
          font-family:'Space Mono',monospace; font-size:13px;
          font-weight:700; letter-spacing:0.05em;
          padding:13px 28px; border-radius:999px;
          border:1.5px solid rgba(99,210,190,0.45);
          cursor:pointer; transition:all 0.25s ease;
          text-transform:uppercase;
        }
        .outline-btn:hover { border-color:#63d2be; background:rgba(99,210,190,0.08); }

        .nav-link {
          font-family:'Space Mono',monospace; font-size:12px;
          color:#5a8880; text-decoration:none; letter-spacing:0.06em;
          text-transform:uppercase; transition:color 0.2s;
        }
        .nav-link:hover { color:#63d2be; }

        .section-label {
          font-family:'Space Mono',monospace; font-size:11px;
          color:#63d2be; letter-spacing:0.18em; text-transform:uppercase;
          display:flex; align-items:center; gap:10px;
        }
        .section-label::before {
          content:''; display:inline-block; width:28px; height:1px;
          background:#63d2be; opacity:0.6;
        }

        .step-num {
          font-family:'Space Mono',monospace; font-size:52px;
          font-weight:700; color:rgba(99,210,190,0.10);
          line-height:1; margin-bottom:4px;
        }

        .testimonial-card {
          background:rgba(10,24,22,0.8);
          border:1px solid rgba(99,210,190,0.1);
          border-radius:14px; padding:26px 22px;
          backdrop-filter:blur(8px);
        }
        .stars { color:#ffe066; font-size:13px; margin-bottom:10px; }

        @media (max-width:768px) {
          .hero-flex { flex-direction:column !important; }
          .graph-demo { display:none; }
          .features-grid { grid-template-columns:1fr !important; }
          .stats-row { flex-direction:column; gap:30px !important; }
          .steps-grid { grid-template-columns:1fr !important; }
          .testimonials-grid { grid-template-columns:1fr !important; }
          .footer-flex { flex-direction:column; gap:24px !important; }
        }
      `}</style>

      

      {/* NAV */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "18px 48px",
        background: "rgba(6,15,14,0.82)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(99,210,190,0.08)",
      }}>
        <div className="relative" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Logo mark */}
          {/* <svg width="28" height="28" viewBox="0 0 28 28">
            <circle cx="14" cy="14" r="13" fill="none" stroke="#63d2be" strokeWidth="1.5" strokeOpacity="0.5"/>
            <circle cx="14" cy="14" r="4" fill="#63d2be"/>
            <line x1="14" y1="14" x2="4"  y2="6"  stroke="#63d2be" strokeWidth="1.2" strokeOpacity="0.6"/>
            <line x1="14" y1="14" x2="24" y2="6"  stroke="#63d2be" strokeWidth="1.2" strokeOpacity="0.6"/>
            <line x1="14" y1="14" x2="4"  y2="22" stroke="#63d2be" strokeWidth="1.2" strokeOpacity="0.6"/>
            <line x1="14" y1="14" x2="24" y2="22" stroke="#63d2be" strokeWidth="1.2" strokeOpacity="0.6"/>
            <circle cx="4"  cy="6"  r="2.5" fill="#ffe066" fillOpacity="0.8"/>
        <circle cx="24" cy="6"  r="2.5" fill="#ffe066" fillOpacity="0.8"/>
            <circle cx="4"  cy="22" r="2.5" fill="#ffe066" fillOpacity="0.8"/>
            <circle cx="24" cy="22" r="2.5" fill="#ffe066" fillOpacity="0.8"/>
          </svg> */}
          <Image src="/logo.svg" className="w-27! h-7! absolute! top-0! left-0 " alt="Logo" width={28} height={28} />
          <span className="ml-30!" style={{
            fontFamily: "'Space Mono', monospace",
            fontWeight: 700, fontSize: 16, color: "#d4f0eb",
            letterSpacing: "0.04em",
          }}>GraphMind</span>
        </div>

        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          {["Features", "How it works", "Pricing", "Docs"].map(l => (
            <a key={l} href="#" className="nav-link">{l}</a>
          ))}
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button onClick={() => router.push("/auth/login")} className="nav-link" style={{ background: "none", border: "none", cursor: "pointer" }}>Sign in</button>
          <button onClick={() => router.push("/dashboard ")} className="cta-btn" style={{ padding: "10px 22px", fontSize: 11 }}>
            Get started →
          </button>
        </div>
      </nav>

      {/* HERO */}
      <section style={{
        position: "relative", zIndex: 1,
        minHeight: "100vh",
        display: "flex", flexDirection: "column", justifyContent: "center",
        padding: "120px 48px 80px",
        maxWidth: 1200, margin: "0 auto",
      }}>
        <div className="hero-flex" style={{ display: "flex", alignItems: "center", gap: 64 }}>
          {/* Left */}
          <div style={{ flex: 1 }}>
            <div className="section-label fade-up" style={{ marginBottom: 24 }}>
              Visual thinking, reimagined
            </div>
            <h1 className="fade-up delay-1" style={{
              fontFamily: "'Lora', serif",
              fontSize: "clamp(42px,5.5vw,76px)",
              fontWeight: 600,
              lineHeight: 1.08,
              color: "#edfaf7",
              marginBottom: 28,
              letterSpacing: "-0.02em",
            }}>
              Map your mind.<br />
              <span style={{ color: "#63d2be" }}>Build</span> connections.<br />
              <em style={{ color: "#ffe066" }}>Think clearly.</em>
            </h1>
            <p className="fade-up delay-2" style={{
              fontFamily: "'Lora', serif",
              fontSize: 17,
              color: "#7ab8b0",
              lineHeight: 1.8,
              maxWidth: 480,
              marginBottom: 40,
            }}>
              GraphMind is an infinite canvas for building living knowledge graphs —
              where every idea is a node and every relationship is a connection you can explore.
            </p>
            <div className="fade-up delay-3" style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              <button onClick={() => router.push("/auth/login")} className="cta-btn">Start mapping free →</button>
              <button className="outline-btn">▶ Watch demo</button>
            </div>

            <div className="fade-up delay-4" style={{
              marginTop: 48,
              display: "flex", gap: 32,
              borderTop: "1px solid rgba(99,210,190,0.1)",
              paddingTop: 28,
            }}>
              <Stat n="50k+" label="Active graphs" />
              <Stat n="200+" label="Node types" />
              <Stat n="99.9%" label="Uptime" />
            </div>
          </div>

          {/* Right — graph demo */}
          <div className="graph-demo fade-up delay-2" style={{
            flex: "0 0 520px",
            background: "rgba(10,24,22,0.75)",
            border: "1px solid rgba(99,210,190,0.18)",
            borderRadius: 20,
            padding: 24,
            backdropFilter: "blur(12px)",
            boxShadow: "0 0 80px rgba(99,210,190,0.08)",
          }}>
            {/* Toolbar chrome */}
            {/* <div style={{
              display: "flex", alignItems: "center", gap: 8,
              marginBottom: 16, paddingBottom: 14,
              borderBottom: "1px solid rgba(99,210,190,0.1)",
            }}>
              {["#ff5f57", "#ffbd2e", "#28c841"].map(c => (
                <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: 0.8 }} />
              ))}
              <div style={{
                flex: 1, textAlign: "center",
                fontFamily: "'Space Mono', monospace", fontSize: 11,
                color: "#3d7068", letterSpacing: "0.05em",
              }}>project-alpha.graphmind</div>
              <div style={{ display: "flex", gap: 6 }}>
                {["⊕", "⌖", "⤢"].map(s => (
                  <span key={s} style={{ color: "#3d7068", fontSize: 14, cursor: "pointer" }}>{s}</span>
                ))}
              </div>
            </div> */}
            <Image
              src="/logo.svg"
              width={500}
              height={500}    // always provide both width & height
              loading="eager"
              alt="Logo"
              style={{ height: "auto" }} // let CSS control the visual height
            />
            {/* <DemoGraph /> */}
            {/* Bottom toolbar */}
            <div style={{
              marginTop: 14, paddingTop: 14,
              borderTop: "1px solid rgba(99,210,190,0.08)",
              display: "flex", justifyContent: "space-between", alignItems: "center",
            }}>
              <div style={{ display: "flex", gap: 10 }}>
                {["Node", "Edge", "Group", "AI"].map(t => (
                  <span key={t} style={{
                    fontFamily: "'Space Mono', monospace", fontSize: 10,
                    color: t === "Node" ? "#63d2be" : "#3d7068",
                    background: t === "Node" ? "rgba(99,210,190,0.12)" : "transparent",
                    padding: "4px 10px", borderRadius: 6,
                    border: `1px solid ${t === "Node" ? "rgba(99,210,190,0.3)" : "transparent"}`,
                    cursor: "pointer",
                  }}>{t}</span>
                ))}
              </div>
              <span style={{
                fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#3d7068",
              }}>7 nodes · 8 edges</span>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section id="features" style={{
        position: "relative", zIndex: 1,
        padding: "100px 48px",
        maxWidth: 1200, margin: "0 auto",
      }}>
        <div className="section-label" style={{ marginBottom: 20 }}>Capabilities</div>
        <h2 style={{
          fontFamily: "'Lora', serif", fontSize: "clamp(30px,3.5vw,48px)",
          fontWeight: 600, color: "#edfaf7", marginBottom: 56,
          maxWidth: 500, lineHeight: 1.2,
        }}>
          Everything your ideas need to <em>breathe</em>
        </h2>
        <div className="features-grid" style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 20,
        }}>
          <FeatureCard icon="🕸️" title="Infinite Canvas" desc="An unbounded workspace that expands as your thinking does. Pan, zoom, and navigate with zero friction." />
          <FeatureCard icon="⚡" title="Real-time Collab" desc="Invite collaborators and co-edit graphs live. Presence indicators show who's thinking where." />
          <FeatureCard icon="🤖" title="AI Graph Builder" desc="Describe your idea and watch GraphMind generate a connected knowledge graph in seconds." />
          <FeatureCard icon="🔗" title="Smart Edges" desc="Directional, weighted, labeled — edges are first-class citizens with rich relationship data." />
          <FeatureCard icon="📦" title="Node Templates" desc="Start with 200+ built-in node types or design your own with custom schemas and icons." />
          <FeatureCard icon="🌐" title="Export Anywhere" desc="Export to JSON, Markdown, Mermaid, PNG, or embed interactive graphs on any website." />
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" style={{
        position: "relative", zIndex: 1,
        padding: "80px 48px 100px",
        background: "rgba(5,14,12,0.6)",
        borderTop: "1px solid rgba(99,210,190,0.06)",
        borderBottom: "1px solid rgba(99,210,190,0.06)",
      }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div className="section-label" style={{ marginBottom: 20 }}>How it works</div>
          <h2 style={{
            fontFamily: "'Lora', serif", fontSize: "clamp(28px,3vw,44px)",
            fontWeight: 600, color: "#edfaf7", marginBottom: 60,
          }}>
            From blank canvas to <em style={{ color: "#63d2be" }}>clarity</em> in three steps
          </h2>
          <div className="steps-grid" style={{
            display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 32,
          }}>
            {[
              { n: "01", t: "Create a node", d: "Double-click anywhere on the canvas to spawn a node. Type your idea — GraphMind auto-formats it." },
              { n: "02", t: "Draw connections", d: "Drag from any node to another to create a relationship. Label it, weight it, and give it direction." },
              { n: "03", t: "Explore & share", d: "Use the graph explorer to find patterns. Share a live link or export a static snapshot." },
            ].map(s => (
              <div key={s.n} style={{
                padding: "32px 28px",
                border: "1px solid rgba(99,210,190,0.1)",
                borderRadius: 16,
                background: "rgba(8,20,18,0.5)",
              }}>
                <div className="step-num">{s.n}</div>
                <div style={{
                  fontFamily: "'Space Mono', monospace", fontSize: 13, color: "#63d2be",
                  fontWeight: 700, letterSpacing: "0.06em", marginBottom: 10,
                  textTransform: "uppercase",
                }}>{s.t}</div>
                <div style={{
                  fontFamily: "'Lora', serif", fontSize: 14.5,
                  color: "#7ab8b0", lineHeight: 1.75,
                }}>{s.d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section style={{
        position: "relative", zIndex: 1,
        padding: "100px 48px",
        maxWidth: 1200, margin: "0 auto",
      }}>
        <div className="section-label" style={{ marginBottom: 20 }}>Loved by thinkers</div>
        <h2 style={{
          fontFamily: "'Lora', serif", fontSize: "clamp(28px,3vw,44px)",
          fontWeight: 600, color: "#edfaf7", marginBottom: 52,
        }}>
          What our users say
        </h2>
        <div className="testimonials-grid" style={{
          display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20,
        }}>
          {[
            { name: "Anya K.", role: "Product Designer", text: "GraphMind changed how I run design sprints. The live collab alone is worth it — my team gets on the same page instantly." },
            { name: "Ravi M.", role: "PhD Researcher", text: "I've tried every knowledge graph tool. GraphMind is the only one that doesn't slow down my thinking. It gets out of the way." },
            { name: "Sara L.", role: "Engineering Lead", text: "The AI graph builder is uncanny. I described our system architecture in plain English and got a perfect dependency graph." },
          ].map(t => (
            <div key={t.name} className="testimonial-card">
              <div className="stars">★★★★★</div>
              <p style={{
                fontFamily: "'Lora', serif", fontSize: 14.5,
                color: "#8cbfb8", lineHeight: 1.75, marginBottom: 18,
                fontStyle: "italic",
              }}>"{t.text}"</p>
              <div style={{
                fontFamily: "'Space Mono', monospace", fontSize: 11,
                color: "#63d2be", fontWeight: 700,
              }}>{t.name}</div>
              <div style={{
                fontFamily: "'Lora', serif", fontSize: 12,
                color: "#3d7068", marginTop: 2,
              }}>{t.role}</div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA BANNER */}
      <section style={{
        position: "relative", zIndex: 1,
        padding: "0 48px 100px",
        maxWidth: 1200, margin: "0 auto",
      }}>
        <div style={{
          background: "linear-gradient(135deg,rgba(99,210,190,0.12) 0%,rgba(255,224,102,0.06) 100%)",
          border: "1px solid rgba(99,210,190,0.2)",
          borderRadius: 24, padding: "64px 56px",
          textAlign: "center",
          backdropFilter: "blur(12px)",
          position: "relative", overflow: "hidden",
        }}>
          {/* decorative ring */}
          <div style={{
            position: "absolute", top: -80, right: -80,
            width: 300, height: 300,
            border: "1px solid rgba(99,210,190,0.08)",
            borderRadius: "50%",
          }} />
          <div style={{
            position: "absolute", bottom: -60, left: -60,
            width: 220, height: 220,
            border: "1px solid rgba(255,224,102,0.06)",
            borderRadius: "50%",
          }} />

          <h2 style={{
            fontFamily: "'Lora', serif", fontSize: "clamp(28px,3.5vw,50px)",
            fontWeight: 600, color: "#edfaf7", marginBottom: 20,
            lineHeight: 1.15, position: "relative",
          }}>
            Ready to connect your thinking?
          </h2>
          <p style={{
            fontFamily: "'Lora', serif", fontSize: 16,
            color: "#7ab8b0", maxWidth: 480, margin: "0 auto 36px",
            lineHeight: 1.75, position: "relative",
          }}>
            Start free — no credit card needed. Your first graph is one double-click away.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 14, flexWrap: "wrap", position: "relative" }}>
            <button onClick={() => router.push("/auth/login")} className="cta-btn" style={{ fontSize: 14, padding: "15px 34px" }}>
              Create your first graph →
            </button>
            <button className="outline-btn">View pricing</button>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{
        position: "relative", zIndex: 1,
        borderTop: "1px solid rgba(99,210,190,0.08)",
        padding: "40px 48px",
      }}>
        <div className="footer-flex" style={{
          maxWidth: 1200, margin: "0 auto",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <svg width="20" height="20" viewBox="0 0 28 28">
              <circle cx="14" cy="14" r="13" fill="none" stroke="#63d2be" strokeWidth="1.5" strokeOpacity="0.4" />
              <circle cx="14" cy="14" r="4" fill="#63d2be" fillOpacity="0.7" />
            </svg>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 13, color: "#3d7068" }}>
              © 2026 GraphMind
            </span>
          </div>
          <div style={{ display: "flex", gap: 28 }}>
            {["Privacy", "Terms", "Status", "GitHub"].map(l => (
              <a key={l} href="#" className="nav-link" style={{ fontSize: 11 }}>{l}</a>
            ))}
          </div>
        </div>
      </footer>
    </>
  );
}