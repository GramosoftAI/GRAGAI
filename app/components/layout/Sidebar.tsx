"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { IconType } from "react-icons";
import { FiMessageSquare } from "react-icons/fi";
import { FaRobot, FaDatabase, FaChartBar, FaPlug, FaBrain } from "react-icons/fa";
import { SlSettings } from "react-icons/sl";
import { GoGraph } from "react-icons/go";
import { useTheme } from "../provider/ThemeProvider";
import ThemeModeSwitch from "../ui/ThemeModeSwitch";
import { Button } from "antd";
import { MenuUnfoldOutlined, MenuFoldOutlined } from "@ant-design/icons";

type MenuItem = {
  label: string;
  icon: IconType;
  path: string;
};

export const menuItems: MenuItem[] = [
  { label: "Bots", icon: FaRobot, path: "/dashboard/bots" },
  { label: "Knowledge Base", icon: FaDatabase, path: "/dashboard/knowledge-base" },
  { label: "Graph View", icon: GoGraph, path: "/dashboard/graph" },
  { label: "Conversations", icon: FiMessageSquare, path: "/dashboard/conversation" },
  { label: "Analytics", icon: FaChartBar, path: "/dashboard/analytics" },
  { label: "Integrations", icon: FaPlug, path: "/dashboard/integrations" },
  { label: "Settings", icon: SlSettings, path: "/dashboard/settings" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void; // Added onToggle here to handle collapse locally
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { isDark, setMode } = useTheme();
  const [mounted, setMounted] = useState(false);
 
  useEffect(() => {
    setMounted(true);
  
  }, []);

  return (
    <div
      className={`relative h-screen sticky top-0 flex flex-col transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] ${
        collapsed ? "w-24" : "w-80"
      } bg-[var(--app-surface)] text-[var(--app-text)] z-50 border-r border-[var(--app-border)] shadow-xl overflow-hidden`}
    >
      {/* 1. Header Section with Integrated Menu Toggle Button */}
      <div className={`pt-7 px-6 pb-10 flex items-center ${collapsed ? "justify-center" : "justify-between"}`}>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-[18px] bg-[#285d91] text-white flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-900/20">
            <FaBrain size={24} />
          </div>
          {!collapsed && (
            <span className="text-[var(--app-text)] text-2xl font-black tracking-tighter leading-none">
              GRAG
            </span>
          )}
        </div>

        {/* Toggle Button Moved from Header to Sidebar Top Right */}
        {!collapsed && (
          <Button 
            type="text" 
            onClick={onToggle}
            className="flex items-center justify-center w-10 h-10 rounded-xl bg-[var(--app-surface-muted)] text-[var(--app-text)] hover:bg-[var(--app-hover)] transition-all"
            icon={<MenuFoldOutlined className="text-lg" />}
          />
        )}
      </div>

      {/* Mini Toggle Trigger for Collapsed State */}
      {collapsed && (
        <div className="flex justify-center pb-4 px-4">
          <Button 
            type="text" 
            onClick={onToggle}
            className="flex items-center justify-center w-12 h-12 rounded-2xl bg-[var(--app-surface-muted)] text-[var(--app-text)] hover:bg-[var(--app-hover)] transition-all"
            icon={<MenuUnfoldOutlined className="text-xl" />}
          />
        </div>
      )}

      {/* 2. Scrollable Navigation Area */}
      <nav className="flex-1 overflow-y-auto custom-scrollbar px-4 space-y-2">
        {menuItems.map((item) => {
          const isActive = pathname === item.path;
          return (
            <Link
              key={item.path}
              href={item.path}
              className={`group relative flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-300 overflow-hidden ${
                isActive 
                  ? "bg-[#285d91] text-white shadow-lg shadow-blue-900/20" 
                  : "text-slate-400 hover:bg-slate-50 hover:text-[#285d91]"
              } ${collapsed ? "justify-center" : "justify-start"}`}
            >
              {isActive && !collapsed && (
                <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-white rounded-r-full" />
              )}
              
              <item.icon className={`flex-shrink-0 text-xl transition-transform duration-300 ${isActive ? "scale-110" : "group-hover:scale-110"}`} />
              
              {!collapsed && (
                <span className={`text-[17px] font-bold tracking-tight transition-all duration-300 ${isActive ? "ml-1" : ""}`}>
                  {item.label}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* 3. Footer Section (Only Theme Switch remaining) */}
      <div className="mt-auto border-t border-[var(--app-border)] p-6 flex flex-col gap-5 bg-[var(--app-surface)] relative z-20">
        <div className={`flex items-center gap-3 ${collapsed ? "justify-center" : "justify-between"} px-2`}>
          {!collapsed && mounted && (
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 opacity-50">
              {isDark ? "Dark Appearance" : "Light Appearance"}
            </span>
          )}
          <ThemeModeSwitch checked={isDark} onChange={(checked) => setMode(checked ? "dark" : "light")} />
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 0px;
          background: transparent;
        }
        .custom-scrollbar {
          scrollbar-width: none;
          -ms-overflow-style: none;
          }
      `}</style>
    </div>
  );
}




// "use client";

// import Link from "next/link";
// import { useEffect, useState } from "react";
// import { usePathname } from "next/navigation";
// import { IconType } from "react-icons";
// import { FiMessageSquare, FiLogOut } from "react-icons/fi";
// import { FaRobot, FaDatabase, FaChartBar, FaPlug, FaBrain } from "react-icons/fa";
// import { SlSettings } from "react-icons/sl";
// import { GoGraph } from "react-icons/go";
// import { useTheme } from "../provider/ThemeProvider";
// import ThemeModeSwitch from "../ui/ThemeModeSwitch";
// import { Avatar, Tooltip, Button } from "antd";
// import { useRouter } from "next/navigation";
// import { deleteCookie } from "../../config/cookies";

// // ─── Menu config ──────────────────────────────────────────────────────────────

// type MenuItem = {
//   label: string;
//   icon: IconType;
//   path: string;
// };

// export const menuItems: MenuItem[] = [
//   { label: "Bots", icon: FaRobot, path: "/dashboard/bots" },
//   { label: "Knowledge Base", icon: FaDatabase, path: "/dashboard/knowledge-base" },
//   { label: "Graph View", icon: GoGraph, path: "/dashboard/graph" },
//   { label: "Conversations", icon: FiMessageSquare, path: "/dashboard/conversation" },
//   { label: "Analytics", icon: FaChartBar, path: "/dashboard/analytics" },
//   { label: "Integrations", icon: FaPlug, path: "/dashboard/integrations" },
//   { label: "Settings", icon: SlSettings, path: "/dashboard/settings" },
// ];

// interface SidebarProps {
//   collapsed: boolean;
// }

// export default function Sidebar({ collapsed }: SidebarProps) {
//   const pathname = usePathname();
//   const router = useRouter();
//   const { isDark, setMode } = useTheme();
//   const [mounted, setMounted] = useState(false);
//   const [userName, setUserName] = useState("User");

//   useEffect(() => {
//     setMounted(true);
//     // Fetch real username from localStorage
//     const storedName = localStorage.getItem("userName");
//     if (storedName) setUserName(storedName);
//   }, []);

//   const handleLogout = () => {
//     // 1. Clear session data
//     localStorage.clear();
//     deleteCookie("AUTH_TOKEN");
    
//     // 2. Redirect to login
//     router.push("/login");
//   };

//   const getInitials = (name: string) => {
//     return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
//   };

//   return (
//     <div
//       className={`relative h-screen sticky top-0 flex flex-col transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] ${
//         collapsed ? "w-24" : "w-80"
//       } bg-[var(--app-surface)] text-[var(--app-text)] z-50 border-r border-[var(--app-border)] shadow-xl overflow-hidden`}
//     >
//       {/* 1. Header Section (Fixed) */}
//       <div className={`pt-10 px-6 pb-6 ${collapsed ? "flex justify-center" : ""}`}>
//         <div className="flex items-center gap-4">
//           <div className="w-12 h-12 rounded-[18px] bg-[#285d91] text-white flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-900/20">
//             <FaBrain size={24} />
//           </div>
//           {!collapsed && (
//             <span className="text-[var(--app-text)] text-2xl font-black tracking-tighter leading-none">
//               Grag
//             </span>
//           )}
//         </div>
//       </div>

//       {/* 2. Scrollable Navigation Area */}
//       <nav className="flex-1 overflow-y-auto custom-scrollbar px-4 space-y-2">
//         {menuItems.map((item) => {
//           const isActive = pathname === item.path;
//           return (
//             <Link
//               key={item.path}
//               href={item.path}
//               className={`group relative flex items-center gap-4 px-4 py-3.5 rounded-2xl transition-all duration-300 overflow-hidden ${
//                 isActive 
//                   ? "bg-[#285d91] text-white shadow-lg shadow-blue-900/20" 
//                   : "text-slate-400 hover:bg-slate-50 hover:text-[#285d91]"
//               } ${collapsed ? "justify-center" : "justify-start"}`}
//             >
//               {isActive && !collapsed && (
//                 <div className="absolute left-0 top-1/4 bottom-1/4 w-1 bg-white rounded-r-full" />
//               )}
              
//               <item.icon className={`flex-shrink-0 text-xl transition-transform duration-300 ${isActive ? "scale-110" : "group-hover:scale-110"}`} />
              
//               {!collapsed && (
//                 <span className={`text-[17px] font-bold tracking-tight transition-all duration-300 ${isActive ? "ml-1" : ""}`}>
//                   {item.label}
//                 </span>
//               )}
//             </Link>
//           );
//         })}
//       </nav>

//       {/* 3. Footer Section (Fixed at bottom) */}
//       <div className="mt-auto border-t border-[var(--app-border)] p-6 flex flex-col gap-5 bg-[var(--app-surface)] relative z-20">
//         {/* Theme Switch */}
//         <div className={`flex items-center gap-3 ${collapsed ? "justify-center" : "justify-between"} px-2`}>
//           {!collapsed && mounted && (
//             <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 opacity-50">
//               {isDark ? "Dark Appearance" : "Light Appearance"}
//             </span>
//           )}
//           <ThemeModeSwitch checked={isDark} onChange={(checked) => setMode(checked ? "dark" : "light")} />
//         </div>

//         {/* User Card */}
//         <div 
//           className={`flex items-center gap-3 p-3 rounded-2xl bg-[var(--app-surface-muted)] border border-[var(--app-border)] hover:bg-[var(--app-hover)] transition-all duration-300 cursor-pointer group ${
//             collapsed ? "justify-center" : ""
//           }`}
//         >
//           <div className="relative">
//             <Avatar 
//               className="bg-gradient-to-br from-[#285d91] to-[#1d4d7c] text-white font-black border-2 border-white shadow-sm"
//               size={collapsed ? 40 : 44}
//             >
//               {getInitials(userName)}
//             </Avatar>
//             <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-emerald-500 border-2 border-white rounded-full" />
//           </div>
          
//           {!collapsed && (
//             <div className="flex flex-col flex-1 overflow-hidden text-[var(--app-text)]">
//               <span className="font-black text-sm tracking-tight truncate">{userName}</span>
//               <span className="font-bold text-[10px] uppercase tracking-wider truncate opacity-40">Pro Account</span>
//             </div>
//           )}
          
//           <Tooltip title="Log Out" placement="right">
//             <Button
//               type="text"
//               icon={<FiLogOut className="text-slate-400 group-hover:text-red-500 transition-colors" />}
//               onClick={(e) => { e.stopPropagation(); handleLogout(); }}
//               className="flex items-center justify-center"
//             />
//           </Tooltip>
//         </div>
//       </div>

//       <style jsx>{`
//         .custom-scrollbar::-webkit-scrollbar {
//           width: 0px;
//           background: transparent;
//         }
//         .custom-scrollbar {
//           scrollbar-width: none;
//           -ms-overflow-style: none;
//         }
//       `}</style>
//     </div>
//   );
// }
