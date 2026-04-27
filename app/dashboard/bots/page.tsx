"use client"
import { Button, Card, Dropdown, Flex, Typography } from 'antd'
import { useRouter } from 'next/navigation'
import React, { useEffect } from 'react'
import { FaRobot, FaUsers } from "react-icons/fa6"
import { FaRegMessage } from "react-icons/fa6"
import { PlusOutlined, EllipsisOutlined } from '@ant-design/icons'
import useAxios from '../../hooks/useAxios'
//import { AgentListResponse } from '@/components/ui/type'
import { useStore } from '../../hooks/useStore'

const { Title, Text } = Typography

export default function BotsPage() {
    const [hoveredId, setHoveredId] = React.useState<string | null>(null)
    const [hovered2, setHovered2] = React.useState(false)

    const [getCreatedAgentList, res] = useAxios<any>({ endpoint: "GETAGENTLIST" })
    const [deleteAgentList] = useAxios({
        endpoint: "DELETEAGENT",
        successCb() {
            getCreatedAgentList()
        },
    })

    const setAgentList = useStore((state) => state.setAgentList)

    if (res?.data?.agents) {
        const data = res.data.agents.map((agent:any) => ({
            id: agent.id,
            name: agent.name,
            status: agent.is_active ? "active" : "draft" as const,
        }))
        setAgentList(data)
    }

    function deleteAgent(id: string) {
        const isConfirm = window.confirm("Are you sure you want to delete this agent?")
        if (!isConfirm) return
        deleteAgentList({ path: `/${id}` })
    }

    function editAgent(agent: any) {
        console.log("edit agent", agent)
    }

    const router = useRouter()

    useEffect(() => {
        getCreatedAgentList()
    }, [])

    return (
        <Flex vertical gap={20} style={{ width: '100%', height: '100%', padding: 20 }}>
            {/* Header */}
            <Flex style={{width:"100%"}} justify="space-between" align="center">
                <div>
                    <Title level={1} style={{ color: '#fff', margin: 0, fontWeight: 700 }}>
                        Your Bots
                    </Title>
                    <Text style={{ color: '#6b7280' }}>Manage your AI agents and chatbots</Text>
                </div>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    style={{ background: '#22c55e', borderColor: '#22c55e', color: '#000', fontWeight: 600 }}
                    onClick={() => router.push("/dashboard/bots/create")}
                >
                    Create Bot
                </Button>
            </Flex>

            {/* Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, 350px)', gap: 20 }}>
                {res?.data?.agents?.map((agent:any) => (
                    <Card
                        key={agent.id}
                        style={{
                            width: 350,
                            height: 200,
                            background: 'transparent',
                            borderRadius: 12,
                            border: hoveredId === agent.id ? '2px solid #4ade80' : '1px solid #2a2a2a',
                            transition: 'border 0.2s',
                        }}
                        bodyStyle={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
                        onMouseEnter={() => setHoveredId(agent.id)}
                        onMouseLeave={() => setHoveredId(null)}
                    >
                        {/* Top row */}
                        <Flex justify="space-between" align="flex-start">
                            <Flex
                                align="center"
                                justify="center"
                                style={{ width: 40, height: 40, background: '#052e16', borderRadius: 8 }}
                            >
                                <FaRobot style={{ color: '#4ade80', fontSize: 18 }} />
                            </Flex>
                            <Flex align="center" gap={8}>
                                <span style={{
                                    fontSize: 12,
                                    background: '#2d2d2d',
                                    color: '#9ca3af',
                                    padding: '2px 12px',
                                    borderRadius: 9999,
                                }}>
                                    {agent.is_active ? "active" : "draft"}
                                </span>
                                <Dropdown
                                    menu={{
                                        items: [
                                            { key: 'edit', label: 'Edit', onClick: () => editAgent(agent) },
                                            {
                                                key: 'delete',
                                                label: <span style={{ color: '#ef4444' }}>Delete...</span>,
                                                onClick: () => deleteAgent(agent.id),
                                            },
                                        ],
                                    }}
                                    trigger={['click']}
                                >
                                    <EllipsisOutlined style={{ color: '#22c55e', fontSize: 16, cursor: 'pointer', transform: 'rotate(90deg)' }} />
                                </Dropdown>
                            </Flex>
                        </Flex>

                        {/* Middle */}
                        <div>
                            <Text strong style={{ color: '#fff', fontSize: 15, display: 'block' }}>{agent.name}</Text>
                            <Text style={{ color: '#6b7280', fontSize: 13 }}>{agent.description ?? "No description"}</Text>
                        </div>

                        {/* Bottom */}
                        <Flex gap={16} align="center">
                            <Flex align="center" gap={4} style={{ color: '#4b5563', fontSize: 13 }}>
                                <FaRegMessage size={14} />
                                <span>0</span>
                            </Flex>
                            <Flex align="center" gap={4} style={{ color: '#4b5563', fontSize: 13 }}>
                                <FaUsers size={14} />
                                <span>0</span>
                            </Flex>
                        </Flex>
                    </Card>
                ))}

                {/* Create New Bot card */}
                <Card
                    style={{
                        width: 350,
                        height: 200,
                        background: 'transparent',
                        borderRadius: 12,
                        border: hovered2 ? '2px dashed #4ade80' : '2px dashed #2d6a4f',
                        transition: 'border-color 0.2s',
                        cursor: 'pointer',
                    }}
                    bodyStyle={{ padding: 16, height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}
                    onMouseEnter={() => setHovered2(true)}
                    onMouseLeave={() => setHovered2(false)}
                    onClick={() => router.push("/dashboard/bots/create")}
                >
                    <span style={{ fontSize: 28, color: hovered2 ? '#4ade80' : '#4a7c59' }}>+</span>
                    <Text style={{ color: hovered2 ? '#4ade80' : '#4a7c59', fontSize: 14 }}>Create New Bot</Text>
                </Card>
            </div>
        </Flex>
    )
}