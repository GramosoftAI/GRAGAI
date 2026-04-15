"use client"
import { NativeSelect } from '@chakra-ui/react'
import { useStore } from '@/lib/hooks/useStore'
import React from 'react'

interface AgentListProps {
  selectedId?: string
  onChange: (id: string, name: string) => void
}



export default function AgentList({ selectedId, onChange }: AgentListProps) {
  // const agentList = [{ id: '1', name: 'Agent 1' }, { id: '2', name: 'Agent 2' }]
  const agentList =useStore((state) => state.agentList)
  

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const id = e.target.value
    const found = agentList?.find((agent) => agent.id === id)
    if (found) onChange(found.id, found.name)
  }

  return (
    <NativeSelect.Root size="sm" width="160px" bg="transparent">
      <NativeSelect.Field
        value={selectedId ?? ''}
        onChange={handleChange}
        style={{ background: '#111', border: '1px solid #2d2d2d', color: '#fff', borderRadius: 8 }}
      >
        <option value="" disabled style={{ background: 'black', color: '#555' }}>
          Select agent
        </option>
        {agentList?.map((agent) => (
          <option key={agent.id} value={agent.id} style={{ background: 'black', color: '#fff' }}>
            {agent.name}
          </option>
        ))}
      </NativeSelect.Field>
      <NativeSelect.Indicator />
    </NativeSelect.Root>
  )
}