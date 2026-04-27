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
  const [request,res] = useAxios({ endpoint: "KNOWLEDGEBASE" })

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
      request({ data: formData as unknown as Record<string, unknown>, path: `/${agent.id}/sources/pdf`, isFormData: true, transformRequest: [(data: unknown) => data] } as any)
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
          <h1 style={{ color: '#fff', fontSize: 28, fontWeight: 700, margin: 0 }}>Knowledge Base</h1>
          <Text style={{ color: '#6b7280', fontSize: 13, marginTop: 8, display: 'block' }}>
            Upload and manage data sources for your bots
          </Text>
        </div>
        <Flex gap={12} align="center">
          <AgentList
            selectedId={agent?.id}
            onChange={(id:string, name:string) => setAgent({ id, name })}
          />
          <Button
            style={{ border: '1px solid #2d2d2d', color: '#fff', background: 'transparent', borderRadius: 8 }}
          >
            View Graph
          </Button>
        </Flex>
      </Flex>

      {/* Adding sources banner */}
      <div style={{ background: 'transparent', border: '1px solid #1a3a28', borderRadius: 10, padding: '14px 18px' }}>
        <Flex align="center" gap={16}>
          <div style={{ width: 36, height: 36, background: '#0f2d1f', border: '1px solid #1a4a2e', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <FileText size={16} color="#22c55e" />
          </div>
          <div>
            <Text style={{ color: '#d1d5db', fontSize: 13, display: 'block' }}>
              Adding sources to:{' '}
              <span style={{ color: '#22c55e', fontWeight: 600 }}>{agent?.name ?? 'None selected'}</span>
            </Text>
            <Text style={{ color: '#4b5563', fontSize: 11, marginTop: 2, display: 'block' }}>0 sources loaded</Text>
          </div>
        </Flex>
      </div>

      {/* Upload box */}
      <div style={{ background: 'transparent', border: '1px solid #1f1f1f', borderRadius: 10, padding: 20 }}>
        <Flex vertical gap={16}>

          {/* Tabs */}
          <Flex gap={4}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  background: activeTab === tab.id ? '#22c55e' : 'transparent',
                  color: activeTab === tab.id ? '#000' : '#888',
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
                style={{ flex: 1, background: '#111', border: '1px solid #1f1f1f', color: '#ccc', fontSize: 13, padding: '10px 14px', borderRadius: 8, outline: 'none' }}
              />
              <button
                onClick={handleSubmit}
                style={{ background: '#22c55e', color: '#000', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px', fontSize: 13 }}
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
                  style={{ border: '1px solid #1a3a28', borderRadius: 10, padding: '12px 16px', background: '#0f2d1f' }}
                >
                  <Flex align="center" gap={12}>
                    <FileText size={16} color="#22c55e" />
                    <div>
                      <Text style={{ color: '#fff', fontSize: 13, display: 'block' }}>{selectedFile.name}</Text>
                      <Text style={{ color: '#4b7a5e', fontSize: 11 }}>{(selectedFile.size / 1024).toFixed(1)} KB</Text>
                    </div>
                  </Flex>
                  <div onClick={() => setSelectedFile(null)} style={{ cursor: 'pointer', color: '#666', display: 'flex' }}>
                    <X size={14} />
                  </div>
                </Flex>
              ) : (
                <div
                  style={{ border: '2px dashed #22c55e55', borderRadius: 10, padding: '48px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, cursor: 'pointer', background: 'transparent' }}
                  onClick={() => document.getElementById('pdf-input')?.click()}
                >
                  <Upload size={28} color="#4b9e6e" />
                  <Text style={{ color: '#6b7280', fontSize: 13 }}>Click to upload PDF, TXT, MD, CSV, or JSON files</Text>
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
                style={{ background: selectedFile ? '#22c55e' : '#1a3a28', color: selectedFile ? '#000' : '#4b7a5e', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: selectedFile ? 'pointer' : 'not-allowed', padding: '10px 18px', width: 'fit-content', fontSize: 13 }}
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
                style={{ background: 'transparent', border: '1px solid #1f1f1f', color: '#ccc', fontSize: 13, borderRadius: 8, resize: 'vertical' }}
              />
              <div>
                <button
                  onClick={handleSubmit}
                  style={{ background: '#22c55e', color: '#000', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px', fontSize: 13 }}
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
      <div style={{ background: 'transparent', border: '1px solid #1f1f1f', borderRadius: 10, overflow: 'hidden' }}>
        <div style={{ padding: '14px 18px', borderBottom: '1px solid #1a1a1a' }}>
          <Text strong style={{ color: '#fff', fontSize: 13 }}>Data Sources</Text>
        </div>
        <div style={{ padding: 40, textAlign: 'center' }}>
          <Text style={{ color: '#4b5563', fontSize: 13 }}>No sources added yet. Upload URLs, files, or text above.</Text>
        </div>
      </div>

    </Flex>
  )
}