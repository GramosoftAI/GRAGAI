"use client"
import { Button, Flex, Input, Typography } from 'antd'
import React, { useState } from 'react'
import { Globe, FileText, Type, Upload, X } from 'lucide-react'
import AgentList from "../../components/ui/AgentList";
import useAxios from '../../hooks/useAxios'

const { Text } = Typography
const { TextArea } = Input

export default function KnowledgeBasePage() {
  const [activeTab, setActiveTab] = useState<'url' | 'pdf' | 'text'>('url')
  const [url, setUrl] = useState('')
  const [textContent, setTextContent] = useState('')
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [request] = useAxios<unknown, Record<string, unknown> | FormData>({ endpoint: "KNOWLEDGEBASE" })

  const tabs = [
    { id: 'url' as const, label: 'URL', icon: <Globe size={14} /> },
    { id: 'pdf' as const, label: 'PDF', icon: <FileText size={14} /> },
    { id: 'text' as const, label: 'Text', icon: <Type size={14} /> },
  ]

  async function handleSubmit() {
    if (!agent?.id) {
      alert("No agent selected")
      return
    }

    if (activeTab === 'url') {

      request({ data: { agent_id: agent.id, agent_name: agent.name, url }, path: `/${agent.id}/sources/url` })
      return
    }

    if (activeTab === 'pdf') {
      if (!selectedFile) { console.warn("No file selected"); return }
      const formData = new FormData()
      formData.append('agent_id', agent.id)
      formData.append('agent_name', agent.name)
      formData.append('file', selectedFile)
      request({ data: formData, path: `/${agent.id}/sources/pdf`, isFormData: true, transformRequest: [(data: unknown) => data] })
      return
    }

    if (activeTab === 'text') {
      request({ data: { agent_id: agent.id, agent_name: agent.name, text: textContent }, path: `/${agent.id}/sources` })
    }
  }

  return (
    <Flex vertical gap={20} style={{ background: 'transparent' }}>

      {/* Header */}
      <Flex justify="space-between" align="flex-start">
        <div>
          <h1 style={{ color: 'var(--app-text)', fontSize: 38, fontWeight: 700, margin: 0 }}>Knowledge Base</h1>
          <Text style={{ color: 'var(--app-text-muted)', fontSize: 20, marginTop: 8, display: 'block' }}>
            Upload and manage data sources for your bots
          </Text>
        </div>
        <Flex gap={12} align="center">
          <AgentList
            selectedId={agent?.id}
            onChange={(id:string, name:string) => setAgent({ id, name })}
          />
          <Button
            style={{ border: '1px solid var(--app-border)', color: 'var(--app-text-muted)', background: 'var(--app-surface)', borderRadius: 8 }}
          >
            View Graph
          </Button>
        </Flex>
      </Flex>

      {/* Adding sources banner */}
      <div style={{ background: 'var(--app-surface)', border: '1px solid var(--app-border)', borderRadius: 10, padding: '14px 18px' }}>
        <Flex align="center" gap={16}>
          <div style={{ width: 36, height: 36, background: 'var(--app-active-bg)', border: '1px solid var(--app-border)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <FileText size={16} color="var(--app-primary)" />
          </div>
          <div>
            <Text style={{ color: 'var(--app-text-muted)', fontSize: 18, display: 'block' }}>
              Adding sources to:{' '}
              <span style={{ color: 'var(--app-primary)', fontWeight: 600 }}>{agent?.name ?? 'None selected'}</span>
            </Text>
            <Text style={{ color: 'var(--app-text-soft)', fontSize: 15, marginTop: 2, display: 'block' }}>0 sources loaded</Text>
          </div>
        </Flex>
      </div>

      {/* Upload box */}
      <div style={{ background: 'var(--app-surface)', border: '1px solid var(--app-border)', borderRadius: 10, padding: 20 }}>
        <Flex vertical gap={16}>

          {/* Tabs */}
          <Flex gap={4}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  background: activeTab === tab.id ? 'var(--app-primary)' : 'transparent',
                  color: activeTab === tab.id ? 'var(--app-on-primary)' : 'var(--app-text-muted)',
                  fontWeight: activeTab === tab.id ? 700 : 400,
                  borderRadius: 8,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  border: 'none',
                  cursor: 'pointer',
                  padding: '6px 14px',
                  fontSize: 13,
                }}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </Flex>

          {/* URL Tab */}
          {activeTab === 'url' && (
            <Flex gap={12} align="center">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://docs.example.com"
                style={{ flex: 1, background: 'var(--app-surface-muted)', border: '1px solid var(--app-border)', color: 'var(--app-text)', fontSize: 16, padding: '10px 14px', borderRadius: 8, outline: 'none' }}
              />
              <button
                onClick={handleSubmit}
                style={{ background: 'var(--app-primary)', color: 'var(--app-on-primary)', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px', fontSize: 16 }}
              >
                <Upload size={14} />
                Crawl
              </button>
            </Flex>
          )}

          {/* PDF Tab */}
          {activeTab === 'pdf' && (
            <Flex vertical gap={12}>
              {selectedFile ? (
                <Flex
                  align="center"
                  justify="space-between"
                  style={{ border: '1px solid var(--app-border)', borderRadius: 10, padding: '12px 16px', background: 'var(--app-surface-muted)' }}
                >
                  <Flex align="center" gap={12}>
                    <FileText size={16} color="var(--app-primary)" />
                    <div>
                      <Text style={{ color: 'var(--app-text)', fontSize: 15, display: 'block' }}>{selectedFile.name}</Text>
                      <Text style={{ color: 'var(--app-text-soft)', fontSize: 13 }}>{(selectedFile.size / 1024).toFixed(1)} KB</Text>
                    </div>
                  </Flex>
                  <div onClick={() => setSelectedFile(null)} style={{ cursor: 'pointer', color: 'var(--app-text-soft)', display: 'flex' }}>
                    <X size={14} />
                  </div>
                </Flex>
              ) : (
                <div
                  style={{ border: '2px dashed var(--app-border)', borderRadius: 10, padding: '48px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, cursor: 'pointer', background: 'transparent' }}
                  onClick={() => document.getElementById('pdf-input')?.click()}
                >
                  <Upload size={28} color="var(--app-primary)" />
                  <Text style={{ color: 'var(--app-text-muted)', fontSize: 16 }}>Click to upload PDF, TXT, MD, CSV, or JSON files</Text>
                </div>
              )}

              <input
                id="pdf-input"
                type="file"
                accept=".pdf,.txt,.md,.csv,.json"
                style={{ display: 'none' }}
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />

              <button
                onClick={handleSubmit}
                disabled={!selectedFile}
                style={{ background: selectedFile ? 'var(--app-primary)' : 'var(--app-border)', color: selectedFile ? 'var(--app-on-primary)' : 'var(--app-text-soft)', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: selectedFile ? 'pointer' : 'not-allowed', padding: '10px 18px', width: 'fit-content', fontSize: 16 }}
              >
                <Upload size={14} />
                Upload
              </button>
            </Flex>
          )}

          {/* Text Tab */}
          {activeTab === 'text' && (
            <Flex vertical gap={12}>
              <TextArea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Paste your text content here..."
                rows={5}
                style={{ background: 'var(--app-surface-muted)', border: '1px solid var(--app-border)', color: 'var(--app-text)', fontSize: 16, borderRadius: 8, resize: 'vertical' }}
              />
              <div>
                <button
                  onClick={handleSubmit}
                  style={{ background: 'var(--app-primary)', color: 'var(--app-on-primary)', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px', fontSize: 16 }}
                >
                  <Upload size={14} />
                  Process
                </button>
              </div>
            </Flex>
          )}

        </Flex>
      </div>

      {/* Data Sources */}
      <div style={{ background: 'var(--app-surface)', border: '1px solid var(--app-border)', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--app-border)' }}>
          <Text strong style={{ color: 'var(--app-text)', fontSize: 16 }}>Data Sources</Text>
        </div>
        <div style={{ padding: 40, textAlign: 'center' }}>
          <Text style={{ color: 'var(--app-text-muted)', fontSize: 16 }}>No sources added yet. Upload URLs, files, or text above.</Text>
        </div>
      </div>

    </Flex>
  )
}
