"use client"
import { Box, Flex } from "@chakra-ui/react";
// import { FaRobot, FaDatabase } from "react-icons/fa6";
// import { SlSettings } from "react-icons/sl";
import Image from "next/image";
import { MdOutlineSpaceDashboard } from "react-icons/md";
import Link from "next/link";
import { useEffect, useState } from "react";
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
    const [open, setOpen] = useState<boolean>(true)
    useEffect(() => {
        console.log(open)
    })

    return (
        <Flex className="min-h-screen text-[#d4f0eb]" style={{ background: "#060f0e" }}>
            {/* ← Background animation added here */}
            {/* <GraphCanvas /> */}

            {/* large screen */}
            <Flex className="w-full " style={{ zIndex: 1 }}>
                {/* Sidebar */}
                {open &&
                    <Flex className="min-h-screen hidden! lg:flex!">
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
                    </Flex>}
                {!open && <Flex className="min-h-screen hidden! sm:flex!">
                    <Box className="w-18 sticky top-0 h-screen flex-shrink-0" style={{ backdropFilter: "blur(16px)", borderRight: "1px solid rgba(99,210,190,0.08)" }}>
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
                                        </Flex></Link>))}</Flex>
                        </Flex>
                    </Box>
                </Flex>
                }

                {/* Main content */}
                <div className="w-full p-2 flex flex-col jus">
                    <Flex direction="column" className=" sticky! top-0!">
                        <Flex className="w-full bg-gray-900 h-15 px-3!" align="center" justify="space-between">
                            <Flex gap={5} align="center">
                                <MdOutlineSpaceDashboard onClick={() => setOpen(!open)} />
                                <div>Dashboard</div>
                            </Flex>
                            <Box className="sm:hidden!">
                                {open ?
                                    <SlSettings onClick={() => setOpen(!open)} /> :
                                    <MdOutlineSpaceDashboard onClick={() => setOpen(!open)} />
                                }
                            </Box>
                        </Flex>
                        {open &&
                            <Flex className="sm:hidden! bg-black w-full! " style={{ zIndex: 10 }}>
                                <Box>
                                    {menuItems.map((item, index) => (
                                        <Link onClick={() => setOpen(!open)}
                                            className={`!mx-4 !mb-2 rounded-xl !text-lg !p-2 hover:!bg-gray-900 hover:!text-green-300 ${pathname === item.path
                                                ? "!bg-gray-900 !text-green-300" : "font-extrabold"
                                                }`}
                                            href={item.path}
                                            key={index}
                                        >
                                            <Flex align="center" gap="3" cursor="pointer">
                                                <span>{item.label}</span>
                                            </Flex>
                                        </Link>
                                    ))}
                                </Box>
                            </Flex>}
                    </Flex>
                    <Box p="5" py="8">
                        {children}
                    </Box>
                </div>
            </Flex>
        </Flex>
    );
}