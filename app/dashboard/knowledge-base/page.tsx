"use client"
import { Box, Button, Flex, NativeSelect, Textarea } from '@chakra-ui/react'
import React, { useState } from 'react'
import { Globe, FileText, Type, Upload } from 'lucide-react'

export default function KnowledgeBasePage() {
  const [activeTab, setActiveTab] = useState<'url' | 'pdf' | 'text'>('url')
  const [url, setUrl] = useState('')
  const [textContent, setTextContent] = useState('')

  const tabs = [
    { id: 'url' as const, label: 'URL', icon: <Globe size={14} /> },
    { id: 'pdf' as const, label: 'PDF', icon: <FileText size={14} /> },
    { id: 'text' as const, label: 'Text', icon: <Type size={14} /> },
  ]

  return (
    <Flex direction="column" gap="5" bg="transparent">

      {/* Header */}
      <Flex justifyContent="space-between" alignItems="flex-start">
        <Box>
          <h1 className="text-3xl! font-bold! text-white!">Knowledge Base</h1>
          <p className="text-sm! mt-2! text-gray-500!">Upload and manage data sources for your bots</p>
        </Box>
        <Flex gap="3" alignItems="center">
          <Box>
            <NativeSelect.Root size="sm" width="160px"  bg="transparent">
              <NativeSelect.Field
                style={{ background: '#111', border: '1px solid #2d2d2d', color: '#fff', borderRadius: 8 }}
              >
                <option value="test">test</option>
                <option value="react">React</option>
                <option value="vue">Vue</option>
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
          </Box>
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
      <Box
        style={{ background: 'transparent', border: '1px solid #1a3a28', borderRadius: 10, padding: '14px 18px' }}
      >
        <Flex alignItems="center" gap="4">
          <Box
            style={{
              width: 36, height: 36,
              background: '#0f2d1f',
              border: '1px solid #1a4a2e',
              borderRadius: 8,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <FileText size={16} color="#22c55e" />
          </Box>
          <Box>
            <p className="text-sm! text-gray-300!">
              Adding sources to: <span className="text-green-500! font-semibold!">test</span>
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
                style={{
                  flex: 1,
                  background: '#111',
                  border: '1px solid #1f1f1f',
                  color: '#ccc',
                  fontSize: 13,
                  padding: '10px 14px',
                  borderRadius: 8,
                  outline: 'none',
                }}
              />
              <Button
                size="sm"
                style={{ background: 'transparent', color: '#000', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px' }}
              >
                <Upload size={14} />
                Crawl
              </Button>
            </Flex>
          )}

          {/* PDF Tab */}
          {activeTab === 'pdf' && (
            <Box
              style={{
                border: '2px dashed #22c55e55',
                borderRadius: 10,
                padding: '48px 20px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                cursor: 'pointer',
                background: 'transparent',
              }}
              onClick={() => document.getElementById('pdf-input')?.click()}
            >
              <input id="pdf-input" type="file" accept=".pdf,.txt,.md,.csv,.json" style={{ display: 'none' }} />
              <Upload size={28} color="#4b9e6e" />
              <p className="text-sm! text-gray-500!">Click to upload PDF, TXT, MD, CSV, or JSON files</p>
            </Box>
          )}

          {/* Text Tab */}
          {activeTab === 'text' && (
            <Flex direction="column" gap="3">
              <Textarea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="Paste your text content here..."
                rows={5}
                style={{
                  background: 'transparent',
                  border: '1px solid #1f1f1f',
                  color: '#ccc',
                  fontSize: 13,
                  padding: '10px 14px',
                  borderRadius: 8,
                  outline: 'none',
                  resize: 'vertical',
                }}
              />
              <Box>
                <Button
                  size="sm"
                  style={{ background: 'transparent', color: '#000', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px' }}
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