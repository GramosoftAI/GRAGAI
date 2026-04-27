"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconType } from "react-icons";
import { FiMessageSquare } from "react-icons/fi";
import { FaRobot, FaDatabase, FaInbox, FaChartBar, FaPlug } from "react-icons/fa";
import { SlSettings } from "react-icons/sl";
import { GoGraph } from "react-icons/go";


// ─── Menu config ──────────────────────────────────────────────────────────────

type MenuItem = {
  label: string;
  icon: IconType;
  path: string;
};

export const menuItems: MenuItem[] = [
  { label: "Bots", icon: FaRobot, path: "/dashboard/bots" },
  { label: "Knowledge Base", icon: FaDatabase, path: "/dashboard/knowledge-base" },
  { label: "Conversation", icon: FiMessageSquare, path: "/dashboard/conversation" },
  // { label: "Inbox", icon: FaInbox, path: "/dashboard/inbox" },
  { label: "Graph", icon: GoGraph, path: "/dashboard/graph" },
  { label: "Analytics", icon: FaChartBar, path: "/dashboard/analytics" },
  { label: "Integrations", icon: FaPlug, path: "/dashboard/integrations" },
  { label: "Settings", icon: SlSettings, path: "/dashboard/settings" },
];

interface SidebarProps {
  collapsed: boolean;
}

export default function Sidebar({ collapsed }: SidebarProps) {
  const pathname = usePathname();

  return (
    <div
      style={{
        width: collapsed ? "72px" : "224px",
        minHeight: "100vh",
        position: "sticky",
        top: 0,
        height: "100vh",
        flexShrink: 0,
        backdropFilter: "blur(16px)",
        borderRight: "1px solid rgba(99,210,190,0.08)",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
        transition: "width 0.25s ease",
        overflow: "hidden",
      }}
    >
      {/* Logo */}
      <div style={{ marginTop: "10px", paddingLeft: "12px" }}>
        <Image
          src="/logo.svg"
          width={50}
          height={50}
          loading="eager"
          alt="Logo"
          style={{ height: "auto" }}
        />
      </div>

      {/* Nav items */}
      <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        {menuItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              style={{
                display: "flex",
                alignItems: "center",
                gap: collapsed ? 0 : "12px",
                margin: "0 16px 8px",
                padding: "8px",
                borderRadius: "12px",
                fontSize: "18px",
                color: isActive ? "#86efac" : "#d4f0eb",
                background: isActive ? "#111827" : "transparent",
                fontWeight: isActive ? 400 : 800,
                textDecoration: "none",
                whiteSpace: "nowrap",
                overflow: "hidden",
                transition: "background 0.2s, color 0.2s",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "#111827";
                  (e.currentTarget as HTMLElement).style.color = "#86efac";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "#d4f0eb";
                }
              }}
            >
              <item.icon style={{ flexShrink: 0 }} />
              {!collapsed && <span style={{ fontSize: "14px" }}>{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}