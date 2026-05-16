"use client";

import { SearchOutlined, BellOutlined, MenuUnfoldOutlined, MenuFoldOutlined, SettingOutlined } from "@ant-design/icons";
import { menuItems } from "./Sidebar";
import { Button, Input, Badge } from "antd";
import { usePathname } from "next/navigation";

interface HeaderProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Header({
  collapsed,
  onToggle,
}: HeaderProps) {
  const pathname = usePathname();
  const currentPage = menuItems.find(item => item.path === pathname)?.label || "Dashboard";

  return (
    <header className="sticky top-0 z-[60] w-full h-24 flex flex-col justify-center bg-[var(--app-surface)]/80 backdrop-blur-xl border-b border-[var(--app-border)] px-6 md:px-10 transition-all">
      <div className="flex items-center justify-between w-full max-w-[1600px] mx-auto">
        {/* Left Side: Navigation Info */}
        <div className="flex items-center gap-4 md:gap-6">
          {/* Main Toggle Button */}
          <Button 
            type="text" 
            onClick={onToggle}
            className="flex items-center justify-center w-12 h-12 rounded-2xl bg-[var(--app-surface-muted)] text-[var(--app-text)] hover:bg-[var(--app-hover)] transition-all"
            icon={collapsed ? <MenuUnfoldOutlined className="text-xl" /> : <MenuFoldOutlined className="text-xl" />}
          />
          
          <div className="flex flex-col">
            <div className="flex items-center gap-2 text-[var(--app-text-muted)] font-black text-[10px] uppercase tracking-[0.2em]">
              Workspace / {currentPage}
            </div>
            <h2 className="text-[var(--app-text)] font-black text-xl md:text-2xl tracking-tighter leading-none mt-1">
              {currentPage}
            </h2>
          </div>
        </div>

        {/* Center: Visual Search (Non-functional) */}
        <div className="hidden xl:flex flex-1 max-w-md mx-12">
          <Input 
            prefix={<SearchOutlined className="text-[var(--app-text-muted)] mr-2" />}
            placeholder="Search your knowledge base..."
            className="h-12 !bg-[var(--app-surface-muted)] !border-none !rounded-2xl font-bold text-[var(--app-text)] placeholder:text-[var(--app-text-muted)] focus:!ring-2 focus:!ring-[#285d91]/10"
          />
        </div>

        {/* Right Side: Quick Actions */}
        <div className="flex items-center gap-2 md:gap-4">
          <Badge count={3} offset={[-4, 4]} color="#285d91">
            <Button 
              type="text" 
              className="w-10 h-10 md:w-12 md:h-12 rounded-2xl bg-[var(--app-surface-muted)] flex items-center justify-center text-[var(--app-text)] hover:bg-[var(--app-hover)] transition-all"
              icon={<BellOutlined className="text-xl" />}
            />
          </Badge>
          
          <Button 
            type="text" 
            className="w-10 h-10 md:w-12 md:h-12 rounded-2xl bg-[var(--app-surface-muted)] flex items-center justify-center text-[var(--app-text)] hover:bg-[var(--app-hover)] transition-all"
            icon={<SettingOutlined className="text-xl" />}
          />
        </div>
      </div>
    </header>
  );
}
