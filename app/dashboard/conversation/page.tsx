"use client"
import { Box, Flex, NativeSelect } from '@chakra-ui/react'
import React, { useState, useRef, useEffect } from 'react'
import { LuBot } from 'react-icons/lu'
import { FiUser, FiSend } from 'react-icons/fi'
import { MdBarChart } from 'react-icons/md'
import { PiGraphLight } from 'react-icons/pi'
import AgentList from '@/components/ui/AgentList'

type Bot = {
  id: string
  name: string
}

type Message = {
  role: 'user' | 'assistant'
  content: string
  confidence?: number
  nodes?: number
}



const AGENT_RESPONSE = (userInput: string): Message => ({
  role: 'assistant',
  content: `Based on your knowledge graph, I found relevant information about "${userInput}". The graph shows connections between nodes that help answer your question with high confidence.`,
  confidence: 94,
  nodes: 0,
})

export default function ChatPlaygroundPage() {
  
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [confidence] = useState(94)
  const [reasoningText] = useState('No matching nodes found in knowledge base')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Reset chat when bot changes
  useEffect(() => {
    setMessages([])
  }, [])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return

    const userMsg: Message = { role: 'user', content: trimmed }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    // Simulate agent reply after short delay
    setTimeout(() => {
      setMessages((prev) => [...prev, AGENT_RESPONSE(trimmed)])
    }, 600)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSend()
  }

 // const selectedBotName = BOTS.find((b) => b.id === selectedBot)?.name ?? ''

  return (
    <Flex gap={4} style={{ height: 'calc(100vh - 120px)' }}>

      {/* Left: Chat Panel */}
      <Flex
        direction="column"
        flex={1}
        style={{ border: '1px solid #1f2d25', borderRadius: 12, overflow: 'hidden' }}
      >
        {/* Header */}
        <Flex justifyContent="space-between" alignItems="center" px="5" py="4"
          style={{ borderBottom: '1px solid #1a2a20', flexShrink: 0 }}
        >
          <Box>
            <h2 className='text-white! font-bold! text-lg!'>Chat Playground</h2>
            <p className='text-xs! text-gray-500! mt-0.5!'>Test your bot with knowledge graph context</p>
          </Box>

          {/* Bot dropdown */}
          <Box>
            <AgentList/>
          </Box>
        </Flex>

        {/* Messages */}
        <Flex direction="column" flex={1} px="5" py="4" gap={4} overflowY="auto">
          {messages.length === 0 && (
            <Flex flex={1} align="center" justify="center">
              <p style={{ fontSize: 13, color: '#ffffff' }}>
                Send a message to start chatting with <span style={{ color: '#22c55e' }}></span>
              </p>
            </Flex>
          )}

          {messages.map((msg, i) => (
            msg.role === 'user' ? (
              <Flex key={i} justifyContent="flex-end">
                <Box style={{
                  background: '#0f3d2a',
                  border: '1px solid #1a5c3a',
                  borderRadius: 12,
                  padding: '10px 14px',
                  maxWidth: '60%',
                }}>
                  <Flex align="center" gap="2" mb="1">
                    <Box style={{
                      width: 22, height: 22, borderRadius: 6,
                      background: '#22c55e22',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <FiUser size={12} color="#22c55e" />
                    </Box>
                    <span style={{ fontSize: 12, color: '#22c55e', fontWeight: 600 }}>User</span>
                  </Flex>
                  <p style={{ fontSize: 14, color: '#fff' }}>{msg.content}</p>
                </Box>
              </Flex>
            ) : (
              <Flex key={i} justifyContent="flex-start">
                <Box style={{
                  background: '#111a14',
                  border: '1px solid #1f2d1f',
                  borderRadius: 12,
                  padding: '12px 16px',
                  maxWidth: '75%',
                }}>
                  <Flex align="center" gap="2" mb="2">
                    <Box style={{
                      width: 22, height: 22, borderRadius: 6,
                      background: '#22c55e22',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <LuBot size={12} color="#22c55e" />
                    </Box>
                    <span style={{ fontSize: 12, color: '#22c55e', fontWeight: 600 }}>Assistant</span>
                  </Flex>
                  <p style={{ fontSize: 14, color: '#e5e7eb', lineHeight: 1.6 }}>{msg.content}</p>
                  <Flex gap={4} mt="3" align="center">
                    <Flex align="center" gap="1">
                      <MdBarChart size={13} color="#6b7280" />
                      <span style={{ fontSize: 12, color: '#6b7280' }}>{msg.confidence}%</span>
                    </Flex>
                    <Flex align="center" gap="1">
                      <PiGraphLight size={13} color="#6b7280" />
                      <span style={{ fontSize: 12, color: '#6b7280' }}>{msg.nodes} nodes</span>
                    </Flex>
                  </Flex>
                </Box>
              </Flex>
            )
          ))}
          <div ref={bottomRef} />
        </Flex>

        {/* Input bar */}
        <Flex px="4" py="3" gap={3} align="center"
          style={{ borderTop: '1px solid #1a2a20', flexShrink: 0 }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask your bot a question..."
            style={{
              flex: 1,
              background: 'transparent',
              border: '1px solid #2d2d2d',
              color: '#ccc',
              fontSize: 14,
              padding: '10px 14px',
              borderRadius: 8,
              outline: 'none',
            }}
          />
          <button
            onClick={handleSend}
            style={{
              width: 42, height: 42,
              background: '#22c55e',
              border: 'none',
              borderRadius: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer',
              flexShrink: 0,
            }}
          >
            <FiSend size={16} color="#000" />
          </button>
        </Flex>
      </Flex>

      {/* Right: Retrieved Context Panel */}
      <Box style={{
        width: 280,
        flexShrink: 0,
        border: '1px solid #1f2d25',
        borderRadius: 12,
        padding: '20px 18px',
      }}>
        <h3 className='text-white! font-bold! text-base! mb-4!'>Retrieved Context</h3>

        <Flex direction="column" gap={5}>
          <Box>
            <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>Nodes Used</p>
          </Box>

          <Box>
            <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>Reasoning Path</p>
            <p style={{ fontSize: 13, color: '#22c55e' }}>{reasoningText}</p>
          </Box>

          <Box>
            <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>Confidence</p>
            <Box style={{
              width: '100%', height: 6,
              background: '#1a2a20',
              borderRadius: 99,
              overflow: 'hidden',
              marginBottom: 6,
            }}>
              <Box style={{
                width: `${confidence}%`,
                height: '100%',
                background: '#22c55e',
                borderRadius: 99,
              }} />
            </Box>
            <p style={{ fontSize: 13, color: '#22c55e', fontWeight: 600 }}>{confidence}%</p>
          </Box>
        </Flex>
      </Box>

    </Flex>
  )
}