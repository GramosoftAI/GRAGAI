"use client";

import { MenuOutlined, SettingOutlined } from "@ant-design/icons";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { menuItems } from "./Sidebar";

// ─── Header ───────────────────────────────────────────────────────────────────

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileMenuOpen: boolean;
  onMobileMenuToggle: () => void;
}

export default function Header({
  collapsed,
  onToggle,
  mobileMenuOpen,
  onMobileMenuToggle,
}: HeaderProps) {
  const pathname = usePathname();

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 20,
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Top bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: "60px",
          padding: "0 12px",
          background: "#111827",
        }}
      >
        {/* Left: sidebar toggle + title */}
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <MenuOutlined
            onClick={onToggle}
            style={{
              fontSize: "18px",
              cursor: "pointer",
              color: "#d4f0eb",
            }}
          />
          <span style={{ color: "#d4f0eb", fontSize: "15px", fontWeight: 600 }}>
            Dashboard
          </span>
        </div>

        {/* Right: mobile menu toggle (visible only on small screens via inline media trick) */}
        <div className="sm:hidden">
          {mobileMenuOpen ? (
            <SettingOutlined
              onClick={onMobileMenuToggle}
              style={{ fontSize: "18px", cursor: "pointer", color: "#d4f0eb" }}
            />
          ) : (
            <MenuOutlined
              onClick={onMobileMenuToggle}
              style={{ fontSize: "18px", cursor: "pointer", color: "#d4f0eb" }}
            />
          )}
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {mobileMenuOpen && (
        <div
          className="sm:hidden"
          style={{
            background: "#000",
            width: "100%",
            zIndex: 10,
          }}
        >
          {menuItems.map((item) => {
            const isActive = pathname === item.path;
            return (
              <Link
                key={item.path}
                href={item.path}
                onClick={onMobileMenuToggle}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "12px",
                  margin: "0 16px 8px",
                  padding: "8px",
                  borderRadius: "12px",
                  fontSize: "18px",
                  color: isActive ? "#86efac" : "#d4f0eb",
                  background: isActive ? "#111827" : "transparent",
                  fontWeight: isActive ? 400 : 800,
                  textDecoration: "none",
                }}
              >
                <span style={{ fontSize: "14px" }}>{item.label}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}