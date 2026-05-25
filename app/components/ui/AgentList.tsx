"use client"
import { Select } from 'antd'
import { useAgents } from '../../hooks/useAgents'
import React from 'react'
import styles from './AgentList.module.css'

interface AgentListProps {
  selectedId?: string
  onChange: (id: string, name: string) => void
}

export default function AgentList({ selectedId, onChange }: AgentListProps) {
  const { agents: agentList } = useAgents();

  function handleChange(value: string) {
    const found = agentList?.find((agent) => agent.id === value)
    if (found) onChange(found.id, found.name)
  }

  return (
    <div className={styles.dropdownWrapper}>
      <Select
        size="middle"
        value={selectedId ?? undefined}
        onChange={handleChange}
        placeholder="Select agent"
        style={{ width: 160 }} // ✅ removed backgroundColor here
        classNames={{
          popup: { root: styles.dropdown },
        }}
        labelRender={(props) => (
          <span style={{ color: 'var(--app-text-muted)' }}>{props.label}</span>
        )}
        options={agentList?.map((agent) => ({
          value: agent.id,
          label: agent.name,
        }))}
      />
    </div>
  )
}
