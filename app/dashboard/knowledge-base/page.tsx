"use client"
import { Box, Button, Flex, Textarea } from '@chakra-ui/react'
import React, { useState } from 'react'
import { Globe, FileText, Type, Upload, X } from 'lucide-react'
import AgentList from '@/components/ui/AgentList'
import useAxios from '@/lib/hooks/useAxios'

export default function KnowledgeBasePage() {
  const [activeTab, setActiveTab] = useState<'url' | 'pdf' | 'text'>('url')
  const [url, setUrl] = useState('')
  const [textContent, setTextContent] = useState('')
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null) // ✅ track file in state
  const [request, res] = useAxios({ endpoint: "KNOWLEDGEBASE" })

  const tabs = [
    { id: 'url' as const, label: 'URL', icon: <Globe size={14} /> },
    { id: 'pdf' as const, label: 'PDF', icon: <FileText size={14} /> },
    { id: 'text' as const, label: 'Text', icon: <Type size={14} /> },
  ]

  function handleSubmit() {
    if (!agent?.id) {
      console.warn("No agent selected")
      return
    }

    if (activeTab === 'url') {
      request({
        data: { agent_id: agent.id, agent_name: agent.name, url },
        path: `/${agent.id}/sources/url`
      })
      return
    }

    if (activeTab === 'pdf') {
      if (!selectedFile) {
        console.warn("No file selected")
        return
      }

      const formData = new FormData()
      formData.append('agent_id', agent.id)
      formData.append('agent_name', agent.name)
      formData.append('file', selectedFile) // ✅ use state, not DOM query

      request({
        data: formData as unknown as Record<string, unknown>,
        path: `/${agent.id}/sources/pdf`, // ✅ fixed typo
        isFormData: true, // ✅ prevents JSON Content-Type
        transformRequest: [(data: unknown) => data], // ✅ prevents axios serializing FormData
      } as any)
      return
    }

    if (activeTab === 'text') {
      request({
        data: { agent_id: agent.id, agent_name: agent.name, text: textContent },
        path: `/${agent.id}/sources`
      })
    }
  }

  return (
    <Flex direction="column" gap="5" bg="transparent">

      {/* Header */}
      <Flex justifyContent="space-between" alignItems="flex-start">
        <Box>
          <h1 className="text-3xl! font-bold! text-white!">Knowledge Base</h1>
          <p className="text-sm! mt-2! text-gray-500!">Upload and manage data sources for your bots</p>
        </Box>
        <Flex gap="3" alignItems="center">
          <AgentList
            selectedId={agent?.id}
            onChange={(id, name) => setAgent({ id, name })}
          />
          <Button
            variant="outline"
            size="sm"
            style={{ border: '1px solid #2d2d2d', color: '#fff', background: 'transparent', borderRadius: 8 }}
          >
            View Graph
          </Button>
        </Flex>
      </Flex>

      {/* Adding sources banner */}
      <Box style={{ background: 'transparent', border: '1px solid #1a3a28', borderRadius: 10, padding: '14px 18px' }}>
        <Flex alignItems="center" gap="4">
          <Box style={{ width: 36, height: 36, background: '#0f2d1f', border: '1px solid #1a4a2e', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <FileText size={16} color="#22c55e" />
          </Box>
          <Box>
            <p className="text-sm! text-gray-300!">
              Adding sources to:{' '}
              <span className="text-green-500! font-semibold!">{agent?.name ?? 'None selected'}</span>
            </p>
            <p className="text-xs! text-gray-600! mt-0.5!">0 sources loaded</p>
          </Box>
        </Flex>
      </Box>

      {/* Upload box */}
      <Box style={{ background: 'transparent', border: '1px solid #1f1f1f', borderRadius: 10, padding: 20 }}>
        <Flex direction="column" gap="4">

          {/* Tabs */}
          <Flex gap="1">
            {tabs.map((tab) => (
              <Button
                key={tab.id}
                size="sm"
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
                }}
              >
                {tab.icon}
                {tab.label}
              </Button>
            ))}
          </Flex>

          {/* URL Tab */}
          {activeTab === 'url' && (
            <Flex gap="3" alignItems="center">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://docs.example.com"
                style={{ flex: 1, background: '#111', border: '1px solid #1f1f1f', color: '#ccc', fontSize: 13, padding: '10px 14px', borderRadius: 8, outline: 'none' }}
              />
              <Button
                size="sm"
                onClick={handleSubmit}
                style={{ background: '#22c55e', color: '#000', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px' }}
              >
                <Upload size={14} />
                Crawl
              </Button>
            </Flex>
          )}

          {/* PDF Tab */}
          {activeTab === 'pdf' && (
            <Flex direction="column" gap="3">
              {/* ✅ Show selected file name or drop zone */}
              {selectedFile ? (
                <Flex
                  alignItems="center"
                  justifyContent="space-between"
                  style={{ border: '1px solid #1a3a28', borderRadius: 10, padding: '12px 16px', background: '#0f2d1f' }}
                >
                  <Flex alignItems="center" gap="3">
                    <FileText size={16} color="#22c55e" />
                    <Box>
                      <p style={{ color: '#fff', fontSize: 13, margin: 0 }}>{selectedFile.name}</p>
                      <p style={{ color: '#4b7a5e', fontSize: 11, margin: 0 }}>
                        {(selectedFile.size / 1024).toFixed(1)} KB
                      </p>
                    </Box>
                  </Flex>
                  {/* ✅ Clear file button */}
                  <Box
                    onClick={() => setSelectedFile(null)}
                    style={{ cursor: 'pointer', color: '#666' }}
                  >
                    <X size={14} />
                  </Box>
                </Flex>
              ) : (
                <Box
                  style={{ border: '2px dashed #22c55e55', borderRadius: 10, padding: '48px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, cursor: 'pointer', background: 'transparent' }}
                  onClick={() => document.getElementById('pdf-input')?.click()}
                >
                  <Upload size={28} color="#4b9e6e" />
                  <p className="text-sm! text-gray-500!">Click to upload PDF, TXT, MD, CSV, or JSON files</p>
                </Box>
              )}

              {/* ✅ onChange stores file in state */}
              <input
                id="pdf-input"
                type="file"
                accept=".pdf,.txt,.md,.csv,.json"
                style={{ display: 'none' }}
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />

              <Button
                size="sm"
                onClick={handleSubmit}
                disabled={!selectedFile}
                style={{ background: selectedFile ? '#22c55e' : '#1a3a28', color: selectedFile ? '#000' : '#4b7a5e', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: selectedFile ? 'pointer' : 'not-allowed', padding: '10px 18px', width: 'fit-content' }}
              >
                <Upload size={14} />
                Upload
              </Button>
            </Flex>
          )}

          {/* Text Tab */}
          {activeTab === 'text' && (
            <Flex direction="column" gap="3">
              <Textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Paste your text content here..."
                rows={5}
                style={{ background: 'transparent', border: '1px solid #1f1f1f', color: '#ccc', fontSize: 13, padding: '10px 14px', borderRadius: 8, outline: 'none', resize: 'vertical' }}
              />
              <Box>
                <Button
                  size="sm"
                  onClick={handleSubmit}
                  style={{ background: '#22c55e', color: '#000', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px' }}
                >
                  <Upload size={14} />
                  Process
                </Button>
              </Box>
            </Flex>
          )}

        </Flex>
      </Box>

      {/* Data Sources */}
      <Box style={{ background: 'transparent', border: '1px solid #1f1f1f', borderRadius: 10, overflow: 'hidden' }}>
        <Box style={{ padding: '14px 18px', borderBottom: '1px solid #1a1a1a' }}>
          <p className="text-sm! font-semibold! text-white!">Data Sources</p>
        </Box>
        <Box style={{ padding: '40px', textAlign: 'center' }}>
          <p className="text-sm! text-gray-600!">No sources added yet. Upload URLs, files, or text above.</p>
        </Box>
      </Box>

    </Flex>
  )
}