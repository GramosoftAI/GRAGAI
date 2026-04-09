"use client"
import { Box, Flex } from "@chakra-ui/react";
// import { FaRobot, FaDatabase } from "react-icons/fa6";
// import { SlSettings } from "react-icons/sl";
import Image from "next/image";
import { MdOutlineSpaceDashboard } from "react-icons/md";
import Link from "next/link";
import { useEffect, useRef } from "react";
import { IconType } from "react-icons";
import { FiMessageSquare } from "react-icons/fi";
import {
    FaHome,
    FaRobot,
    FaDatabase,
    FaBullhorn,
    FaInbox,
    FaChartBar,
    FaPlug,
} from "react-icons/fa";
import { SlSettings } from "react-icons/sl";
import { usePathname } from "next/navigation";

type MenuItem = {
    label: string;
    icon: IconType;
    path?: string;
};
// ─── Animated Graph Canvas Background ───────────────────────────────────────
// function GraphCanvas() {
//     const canvasRef = useRef<HTMLCanvasElement>(null);

//     useEffect(() => {
//         const canvas = canvasRef.current!;
//         const ctx = canvas.getContext("2d")!;

//         const resize = () => {
//             canvas.width = window.innerWidth;
//             canvas.height = window.innerHeight;
//         };
//         resize();
//         window.addEventListener("resize", resize);

//         type Node = {
//             x: number; y: number; vx: number; vy: number;
//             r: number; opacity: number; pulse: number;
//         };

//         const nodes: Node[] = Array.from({ length: 38 }, () => ({
//             x: Math.random() * window.innerWidth,
//             y: Math.random() * window.innerHeight,
//             vx: (Math.random() - 0.5) * 0.35,
//             vy: (Math.random() - 0.5) * 0.35,
//             r: Math.random() * 3 + 2,
//             opacity: Math.random() * 0.5 + 0.2,
//             pulse: Math.random() * Math.PI * 2,
//         }));

//         let raf: number;

//         const draw = () => {
//             ctx.clearRect(0, 0, canvas.width, canvas.height);

//             // edges
//             for (let i = 0; i < nodes.length; i++) {
//                 for (let j = i + 1; j < nodes.length; j++) {
//                     const dx = nodes[i].x - nodes[j].x;
//                     const dy = nodes[i].y - nodes[j].y;
//                     const dist = Math.sqrt(dx * dx + dy * dy);
//                     if (dist < 180) {
//                         const alpha = (1 - dist / 180) * 0.18;
//                         ctx.beginPath();
//                         ctx.moveTo(nodes[i].x, nodes[i].y);
//                         ctx.lineTo(nodes[j].x, nodes[j].y);
//                         ctx.strokeStyle = `rgba(99,210,190,${alpha})`;
//                         ctx.lineWidth = 1;
//                         ctx.stroke();
//                     }
//                 }
//             }

//             // nodes
//             for (const n of nodes) {
//                 n.pulse += 0.025;
//                 const glow = Math.sin(n.pulse) * 0.3 + 0.7;
//                 const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 3);
//                 grad.addColorStop(0, `rgba(99,210,190,${n.opacity * glow})`);
//                 grad.addColorStop(1, `rgba(99,210,190,0)`);
//                 ctx.beginPath();
//                 ctx.arc(n.x, n.y, n.r * 3, 0, Math.PI * 2);
//                 ctx.fillStyle = grad;
//                 ctx.fill();

//                 ctx.beginPath();
//                 ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
//                 ctx.fillStyle = `rgba(180,255,240,${n.opacity * glow})`;
//                 ctx.fill();

//                 n.x += n.vx;
//                 n.y += n.vy;
//                 if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
//                 if (n.y < 0 || n.y > canvas.height) n.vy *= -1;
//             }

//             raf = requestAnimationFrame(draw);
//         };
//         draw();

//         return () => {
//             cancelAnimationFrame(raf);
//             window.removeEventListener("resize", resize);
//         };
//     }, []);

//     return (
//         <canvas
//             ref={canvasRef}
//             style={{
//                 position: "fixed",
//                 inset: 0,
//                 pointerEvents: "none",
//                 opacity: 0.55,
//                 zIndex: 0,
//             }}
//         />
//     );
// }

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
const pathname = usePathname();
    const menuItems = [
        //   { label: "Dashboard", icon: FaHome, path: "/dashboard" },
        { label: "Bots", icon: FaRobot, path: "/dashboard/bots" },
        { label: "Knowledge Base", icon: FaDatabase, path: "/dashboard/knowledge-base" },
        { label: "Conversation", icon: FiMessageSquare, path: "/dashboard/conversation" },
        { label: "Inbox", icon: FaInbox, path: "/dashboard/inbox" },
        { label: "Analytics", icon: FaChartBar, path: "/dashboard/analytics" },
        { label: "Integrations", icon: FaPlug, path: "/dashboard/integrations" },
        { label: "Settings", icon: SlSettings, path: "/dashboard/settings" },
    ];

    return (
        <Flex className="min-h-screen text-[#d4f0eb]" style={{ background: "#060f0e" }}>
            {/* ← Background animation added here */}
            {/* <GraphCanvas /> */}

            <Flex className="w-full " style={{ zIndex: 1 }}>
                {/* Sidebar */}
                <Flex className="min-h-screen">
                    <Box className="w-2xs sticky top-0 h-screen flex-shrink-0" style={{ backdropFilter: "blur(16px)", borderRight: "1px solid rgba(99,210,190,0.08)" }}>
                        <Flex direction="column" className="gap-5 h-full">
                            <Box className="mt-5!">
                                <Image
                                    src="/logo.svg"
                                    width={100}
                                    height={100}
                                    loading="eager"
                                    alt="Logo"
                                    style={{ height: "auto" }}
                                />
                            </Box>

                            <Flex direction="column" gap="1">
                                {menuItems.map((item, index) => (
                                    <Link
                                        className={`!mx-4 !mb-2 rounded-xl !text-lg !p-2 hover:!bg-gray-900 hover:!text-green-300 ${pathname === item.path
                                                ? "!bg-gray-900 !text-green-300" : "font-extrabold"
                                            }`}
                                        href={item.path}
                                        key={index}
                                    >
                                        <Flex align="center" gap="3" cursor="pointer">
                                            <item.icon />
                                            <span>{item.label}</span>
                                        </Flex>
                                    </Link>
                                ))}
                            </Flex>
                        </Flex>
                    </Box>
                </Flex>

                {/* Main content */}
                <div className="w-full p-2 flex flex-col">
                    <Flex className="w-full bg-gray-900 h-15 px-3!" gap={5} align="center">
                        <MdOutlineSpaceDashboard />
                        <div>Dashboard</div>
                    </Flex>
                    <Box p="5" py="8">
                        {children}
                    </Box>
                </div>
            </Flex>
        </Flex>
    );
}