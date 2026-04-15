"use client"
import { Box, Button, Stack, Card, Flex, Menu, Portal } from '@chakra-ui/react'
import { useRouter } from 'next/navigation'
import React, { use, useEffect,useState } from 'react'
import { FaRobot, FaUsers } from "react-icons/fa6";
import { FaRegMessage } from "react-icons/fa6";
// import {  } from "react-icons/fa";
import { CiMenuKebab } from "react-icons/ci";
import { MdAdd } from "react-icons/md";
import useAxios from '@/lib/hooks/useAxios';
import { AgentItem, AgentListResponse } from '@/components/ui/type';
import { useStore } from '@/lib/hooks/useStore';


export default function BotsPage() {
    const [hovered, setHovered] = React.useState(false)
    const [hovered2, setHovered2] = React.useState(false)
    const [getCreatedAgentList, res] = useAxios<AgentListResponse>({ endpoint: "GETAGENTLIST" });
    const [hoveredId, setHoveredId] = React.useState<string | null>(null);
    const list = [{ status: "active" }]
    const [deleteAgentList,result]=useAxios({endpoint:"DELETEAGENT",successCb() {
        getCreatedAgentList()
    },})

     const setAgentList=useStore((state)=>state.setAgentList)
// const [agentList, setAgentList] = useState<AgentItem[]>([]);

// then store it:
if (res?.data?.agents) {
  const data = res.data.agents.map((agent) => ({
    id: agent.id,
    name: agent.name,
    status: agent.is_active ? "active" : "draft" as const,
  }));
  setAgentList(data);

}
function deleteAgent(id:string){
 console.log("delete agent",id);
 const isConform = window.confirm("Are you sure you want to delete this agent?")
 if(!isConform) return;
 deleteAgentList({path:`/${id}`})
}
function editAgent(agent:any){
    console.log("edit agent",agent)
}
    const router = useRouter()
    useEffect(() => {
        getCreatedAgentList();
    }, [])
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
                <Box className='grid lg:grid-cols-3 md:grid-cols-2 grid-cols-1 gap-5'>
                    {res?.data?.agents?.map((agent) => (
                        <Card.Root
                            key={agent.id}
                            size="sm"
                            className="w-[350px] h-[200px] bg-transparent!"
                            style={{
                                borderRadius: 12,
                                border: hoveredId === agent.id ? '2px solid #4ade80' : '1px solid #2a2a2a',
                                transition: 'border 0.2s',
                            }}
                            onMouseEnter={() => setHoveredId(agent.id)}
                            onMouseLeave={() => setHoveredId(null)}
                        >
                            <Card.Body className="flex flex-col justify-between p-4 h-full">
                                <Flex justifyContent="space-between" alignItems="flex-start">
                                    <Flex
                                        className="bg-green-950 items-center justify-center rounded-lg"
                                        style={{ width: 40, height: 40 }}
                                    >
                                        <FaRobot className="text-green-400" size={18} />
                                    </Flex>
                                    <span className="flex items-center gap-2">
                                        <p className="text-xs! bg-[#2d2d2d] text-gray-400 px-3! py-1! rounded-full!">
                                            {agent.is_active ? "active" : "draft"}
                                        </p>
                                        <Menu.Root>
      <Menu.Trigger asChild>
       <CiMenuKebab size={14} className="text-green-600! text-sm cursor-pointer" />
      </Menu.Trigger>
      <Portal>
        <Menu.Positioner>
          <Menu.Content>
            <Menu.Item value="edit" onClick={()=>editAgent(agent)}>Edit</Menu.Item>
            {/* <Menu.Item value="export">Export</Menu.Item> */}
            <Menu.Item
              value="delete" onClick={()=>deleteAgent(agent.id)}
              color="fg.error"
              _hover={{ bg: "bg.error", color: "fg.error" }}
            >
              Delete...
            </Menu.Item>
          </Menu.Content>
        </Menu.Positioner>
      </Portal>
    </Menu.Root>
                                        
                                    </span>
                                </Flex>

                                <Box>
                                    <p className="text-white font-bold text-base m-0">{agent.name}</p>
                                    <p className="text-gray-500 text-sm m-0">{agent.description ?? "No description"}</p>
                                </Box>

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
                    ))}
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