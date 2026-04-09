"use client"
import { Box, Button, Stack, Card, Flex } from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import React from 'react'
import { FaRobot, FaUsers } from "react-icons/fa6";
import { FaRegMessage } from "react-icons/fa6";
// import {  } from "react-icons/fa";
import { CiMenuKebab } from "react-icons/ci";
import { MdAdd } from "react-icons/md";

export default function BotsPage() {
    const [hovered, setHovered] = React.useState(false)
    const [hovered2, setHovered2] = React.useState(false)

    const list = [{ status: "active" }]
    const router = useRouter()
    return (
        <Flex direction="column" gap="5" className='w-full h-full p-5!'>
            <Flex w="full" justifyContent="space-between">
                <Box>
                    <h1 className='text-4xl! text-white font-bold!'>Your Bots</h1>
                    <p>Manage your AI agents and chatbots</p>
                </Box>
                <Box>
                    <Button onClick={() => { router.push("/dashboard/bots/create") }}> <MdAdd size={18} /> Create Bot</Button>
                </Box>
            </Flex>

            <Flex>
                <Box className='grid grid-cols-3 gap-5'>
                    <Card.Root
                        size="sm"
                        className="w-[350px] h-[200px] bg-transparent!"
                        style={{
                            borderRadius: 12,
                            border: hovered ? '2px solid #4ade80' : '1px solid #2a2a2a',
                            transition: 'border 0.2s',
                        }}
                        onMouseEnter={() => setHovered(true)}
                        onMouseLeave={() => setHovered(false)}
                    >
                        <Card.Body className="flex flex-col justify-between p-4 h-full">

                            {/* Header: icon + status badge */}
                            <Flex justifyContent="space-between" alignItems="flex-start">
                                <Flex
                                    className="bg-green-950 items-center justify-center rounded-lg"
                                    style={{ width: 40, height: 40 }}
                                >
                                    <FaRobot className="text-green-400" size={18} />
                                </Flex>
                                <span className="flex items-center gap-2">
                                    <p className="text-xs! bg-[#2d2d2d] text-gray-400 px-3! py-1! rounded-full!">
                                        draft
                                    </p>
                                    <CiMenuKebab size={14} className="text-green-600! text-sm cursor-pointer" />

                                </span>
                            </Flex>

                            {/* Name + personality */}
                            <Box>
                                <p className="text-white font-bold text-base m-0">test</p>
                                <p className="text-gray-500 text-sm m-0">Friendly personality</p>
                            </Box>

                            {/* Stats row */}
                            <Flex gap={4} alignItems="center">
                                <Flex alignItems="center" gap={1} className="text-gray-600 text-sm">
                                    <FaRegMessage size={14} />
                                    <span>0</span>
                                </Flex>
                                <Flex alignItems="center" gap={1} className="text-gray-600 text-sm">
                                    <FaUsers size={14} />
                                    <span>0</span>
                                </Flex>
                            </Flex>

                        </Card.Body>
                    </Card.Root>
                    <Card.Root
                        size="sm"
                        className="w-[350px] h-[200px] bg-transparent! cursor-pointer"
                        style={{
                            borderRadius: 12,
                            border: hovered2 ? '2px dashed #4ade80' : '2px dashed #2d6a4f',
                            transition: 'border-color 0.2s',
                        }}
                        onMouseEnter={() => setHovered2(true)}
                        onMouseLeave={() => setHovered2(false)}
                        onClick={() => router.push("/dashboard/bots/create")}
                    >
                        <Card.Body className="flex flex-col items-center justify-center h-full gap-2">
                            <span style={{ fontSize: 28, color: hovered2 ? '#4ade80' : '#4a7c59' }}>+</span>
                            <p style={{ color: hovered2 ? '#4ade80' : '#4a7c59', fontSize: 14, margin: 0 }}>
                                Create New Bot
                            </p>
                        </Card.Body>
                    </Card.Root>
                </Box>
            </Flex>

        </Flex>
    )
}