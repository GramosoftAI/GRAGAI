"use client"
import useAxios from '@/lib/hooks/useAxios';
import { Flex, Box, Switch, Textarea, Button, Field, Input } from '@chakra-ui/react';
import { useRouter } from 'next/navigation';
import React, { useState } from 'react'
import { IoArrowBackSharp } from "react-icons/io5";

export default function CreateBotPage() {
    const [createAgent]=useAxios({endpoint:"CREATEAGENT",successCb() {
        router.back()
    },})
    const router = useRouter()
    const [name, setName] = useState('')
   // const [description, setDescription] = useState('')
    const [activePersonality, setActivePersonality] = useState<string>('Friendly')
    const [memory, setMemory] = useState(true)
    const [reasoning, setReasoning] = useState(true)
    const [systemPrompt, setSystemPrompt] = useState(
        'You are a helpful assistant that answers questions based on the provided knowledge base.'
    )

    const buttons: string[] = ["Friendly", "Formal", "Sales", "Technical", "Concise"]

    const handleSave = () => {
        const payload = {
            name,
//description,
            personality: activePersonality,
            system_prompt: systemPrompt,
            memory,
            reasoning,
        }
        createAgent({data:payload})
        console.log(payload)
    }

    return (
        <Flex direction="column" gap={6} className='mb-10! max-w-[75%]!'>

            {/* Header */}
            <Flex gap={2} align="center">
                <button
                    onClick={() => router.back()}
                    className='hover:bg-gray-700! p-2! rounded! text-gray-400! hover:text-white!'
                >
                    <IoArrowBackSharp size={18} />
                </button>
                <Box>
                    <h1 className='text-2xl! text-white! font-bold!'>Create Bot</h1>
                    <p className='text-sm! text-gray-500!'>Configure your AI agent</p>
                </Box>
            </Flex>

            {/* Divider */}
            <Box className='border-b! border-gray-700!' />

            {/* Bot Name */}
            <Field.Root>
                <Field.Label className='text-white! font-semibold! mb-2!'>Bot Name</Field.Label>
                <Input
                    value={name}
                    placeholder="e.g. Support Agent"
                    style={{
                        background: 'transparent',
                        border: '1px solid #2d2d2d',
                        color: '#fff',
                        borderRadius: 8,
                        padding: '10px 14px',
                    }}
                    onChange={(e) => setName(e.target.value)}
                />
            </Field.Root>


            {/* Personality */}
            <Field.Root>
                <Field.Label className='text-white! font-semibold! mb-2!'>Personality</Field.Label>
                <Flex gap="3" flexWrap="wrap">
                    {buttons.map((button, index) => (
                        <button
                            key={index}
                            onClick={() => setActivePersonality(button)}
                            style={{
                                background: activePersonality === button ? '#22c55e' : 'transparent',
                                color: activePersonality === button ? '#000' : '#9ca3af',
                                border: `1px solid ${activePersonality === button ? '#22c55e' : '#374151'}`,
                                padding: '6px 16px',
                                borderRadius: 8,
                                fontWeight: activePersonality === button ? 600 : 400,
                                cursor: 'pointer',
                                fontSize: 14,
                                transition: 'all 0.15s',
                            }}
                        >
                            {button}
                        </button>
                    ))}
                </Flex>
            </Field.Root>

            {/* System Prompt */}
            <Field.Root>
                <Field.Label className='text-white! font-semibold! mb-2!'>System Prompt</Field.Label>
                <Textarea
                    value={systemPrompt}
                    onChange={(e) => setSystemPrompt(e.target.value)}
                    rows={5}
                    style={{
                        background: 'transparent',
                        border: '1px solid #2d2d2d',
                        color: '#ccc',
                        borderRadius: 8,
                        padding: '10px 14px',
                        fontSize: 14,
                        resize: 'vertical',
                        width: '100%',
                    }}
                />
            </Field.Root>

            {/* Divider */}
            <Box className='border-b! border-gray-700!' />

            {/* Capabilities */}
            <Box>
                <h2 className='text-white! font-bold! text-lg! mb-4!'>Capabilities</h2>

                <Flex direction="column" gap={4}>
                    {/* Memory */}
                    <Flex justifyContent="space-between" alignItems="center">
                        <Box>
                            <p className='text-white! font-semibold! text-sm!'>Memory</p>
                            <p className='text-gray-500! text-xs! mt-0.5!'>Remember conversation context</p>
                        </Box>
                        <Switch.Root
                            colorPalette="green"
                            size="lg"
                            checked={memory}
                            onCheckedChange={(e) => setMemory(e.checked)}
                        >
                            <Switch.HiddenInput />
                            <Switch.Control />
                            <Switch.Label />
                        </Switch.Root>
                    </Flex>

                    {/* Divider */}
                    <Box className='border-b! border-gray-800!' />

                    {/* Reasoning */}
                    <Flex justifyContent="space-between" alignItems="center">
                        <Box>
                            <p className='text-white! font-semibold! text-sm!'>Reasoning</p>
                            <p className='text-gray-500! text-xs! mt-0.5!'>Show reasoning path in responses</p>
                        </Box>
                        <Switch.Root
                            colorPalette="green"
                            size="lg"
                            checked={reasoning}
                            onCheckedChange={(e) => setReasoning(e.checked)}
                        >
                            <Switch.HiddenInput />
                            <Switch.Control />
                            <Switch.Label />
                        </Switch.Root>
                    </Flex>
                </Flex>
            </Box>

            {/* Divider */}
            <Box className='border-b! border-gray-700!' />

            {/* Actions */}
            <Flex justifyContent="flex-end" gap={3}>
                <Button
                    onClick={() => router.back()}
                    variant="outline"
                    style={{ border: '1px solid #374151', color: '#9ca3af', background: 'transparent', borderRadius: 8 }}
                >
                    Cancel
                </Button>
                <Button
                    onClick={handleSave}
                    style={{ background: '#22c55e', color: '#000', fontWeight: 700, borderRadius: 8 }}
                >
                    Create Bot
                </Button>
            </Flex>

        </Flex>
    )
}