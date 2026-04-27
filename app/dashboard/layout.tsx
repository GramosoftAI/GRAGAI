"use client";

import { useState } from "react";
import Sidebar from "../components/layout/Sidebar";
import Header from "../components/layout/Header";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Desktop: collapsed/expanded sidebar
  const [collapsed, setCollapsed] = useState(false);

  // Mobile: dropdown menu open/close
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#060f0e",
        color: "#d4f0eb",
        display: "flex",
        width:"100%"
      }}
    >
      {/* Sidebar — hidden on mobile via Tailwind */}
      <div className="hidden lg:flex">
        <Sidebar collapsed={collapsed} />
      </div>

      {/* Main column */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        <Header
          collapsed={collapsed}
          onToggle={() => setCollapsed((prev) => !prev)}
          mobileMenuOpen={mobileMenuOpen}
          onMobileMenuToggle={() => setMobileMenuOpen((prev) => !prev)}
        />

        {/* Page content */}
        <div style={{ padding: "32px 20px", width:"100%" }}>{children}</div>
      </div>
    </div>
  );
}