"use client"
import { Button, Flex, Input, Typography, Card, Row, Col, Segmented } from 'antd'
import { useState, useEffect } from 'react'
import { Globe, FileText, Type, Upload, X } from 'lucide-react'
import AgentList from "../../components/ui/AgentList";
import useAxios from '../../hooks/useAxios'
import type { Agent } from "../../components/ui/type";
import { useStore } from "../../hooks/useStore";
import { useRouter } from 'next/navigation'

const { Text, Title } = Typography
const { TextArea } = Input

type AgentListResponse = {
  data?: {
    agents?: Agent[];
  };
};

export default function KnowledgeBasePage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'url' | 'pdf' | 'text'>('url')
  const [url, setUrl] = useState('')
  const [textContent, setTextContent] = useState('')
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const setAgentList = useStore((state) => state.setAgentList);
  const setBotsCache = useStore((state) => state.setBotsCache);
  const [request] = useAxios<unknown, Record<string, unknown> | FormData>({ endpoint: "KNOWLEDGEBASE" })
  const [getAgents] = useAxios<AgentListResponse>({ endpoint: "GETAGENTLIST", hideErrorMsg: true });

  const tabs = [
    { value: 'url' as const, label: <Flex align="center" gap={6}><Globe size={14} /> URL</Flex> },
    { value: 'pdf' as const, label: <Flex align="center" gap={6}><FileText size={14} /> PDF</Flex> },
    { value: 'text' as const, label: <Flex align="center" gap={6}><Type size={14} /> Text</Flex> },
  ]

  function mapAgentsToList(agents: Agent[]) {
    return agents.map((agent) => ({
      id: agent.id,
      name: agent.name,
      status: agent.is_active ? "active" : "draft",
    }));
  }

  // ─── Persistence Logic ──────────────────────────────────────────────────────
  useEffect(() => {
    getAgents(undefined, (payload) => {
      const agents = payload?.data?.agents ?? [];
      setBotsCache(agents);
      setAgentList(mapAgentsToList(agents));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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
    <div className="w-full min-h-screen p-4 sm:p-6 md:p-10" style={{ background: 'transparent' }}>
      <Flex vertical gap={24}>
        
        {/* Header Section */}
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} md={16}>
            <Title level={1} style={{ color: 'var(--app-text)', margin: 0, fontSize: 'calc(1.8rem + 1vw)', fontWeight: 700 }}>
              Knowledge Base
            </Title>
            <Text style={{ color: 'var(--app-text-muted)', fontSize: 16, marginTop: 4, display: 'block' }}>
              Upload and manage data sources for your artificial intelligence bots
            </Text>
          </Col>
          <Col xs={24} md={8}>
            {/* Handled dynamic alignment cleanly using Tailwind layout utilities instead of strict props */}
            <div className="flex flex-wrap items-center gap-3 justify-start md:justify-end">
              <AgentList
                selectedId={agent?.id}
                onChange={(id: string, name: string) => setAgent({ id, name })}
              />
              <Button
                style={{ 
                  border: '1px solid var(--app-border)', 
                  color: 'var(--app-text-muted)', 
                  background: 'var(--app-surface)', 
                  borderRadius: 8,
                  height: 33
                }}
                onClick={() => router.push("/dashboard/graph")}
              >
                View Graph
              </Button>
            </div>
          </Col>
        </Row>

        {/* Dynamic Context Banner */}
        <div 
          style={{ 
            background: 'var(--app-surface)', 
            border: '1px solid var(--app-border)', 
            borderRadius: 12, 
            padding: '16px 20px',
            transition: 'all 0.3s ease'
          }}
        >
          <Flex align="center" gap={16} wrap>
            <div style={{ 
              width: 42, 
              height: 42, 
              background: 'var(--app-active-bg)', 
              border: '1px solid var(--app-border)', 
              borderRadius: 10, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              flexShrink: 0 
            }}>
              <FileText size={18} color="var(--app-primary)" />
            </div>
            <div>
              <Text style={{ color: 'var(--app-text-muted)', fontSize: 16, display: 'block' }}>
                Adding sources to:{' '}
                <span style={{ color: agent?.name ? 'var(--app-primary)' : 'var(--app-text-soft)', fontWeight: 600 }}>
                  {agent?.name ?? 'No Agent Selected'}
                </span>
              </Text>
              <Text style={{ color: 'var(--app-text-soft)', fontSize: 13, marginTop: 2, display: 'block' }}>
                0 sources loaded
              </Text>
            </div>
          </Flex>
        </div>

        {/* Input Sandbox Container */}
        <Card 
          bordered 
          style={{ 
            background: 'var(--app-surface)', 
            borderColor: 'var(--app-border)', 
            borderRadius: 12 
          }}
          styles={{ body: { padding: '24px' } }}
        >
          <Flex vertical gap={20}>
            {/* Native Tab Alternative via AntD Segmented */}
            <div className="w-full overflow-x-auto no-scrollbar pb-1">
          <Segmented
            options={tabs}
            value={activeTab}
            onChange={(value) => setActiveTab(value as 'url' | 'pdf' | 'text')}
            style={{
              background: 'var(--app-surface-muted)',
              border: '1px solid var(--app-border)',
              padding: 4,
              borderRadius: 8,
              whiteSpace: 'nowrap', // 👈 Prevents text from breaking into lines
            }}
          />
        </div>

            {/* Dynamic Content Views */}
            <div className="w-full mt-2">
              {/* URL Capture Area */}
              {activeTab === 'url' && (
                /* Swapped "width" property out for Tailwind "w-full" assignment */
                <Row gutter={[12, 12]} className="w-full">
                  <Col xs={24} sm={18} md={20}>
                    <input
                      type="text"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://docs.example.com"
                      style={{ 
                        width: '100%',
                        background: 'var(--app-surface-muted)', 
                        border: '1px solid var(--app-border)', 
                        color: 'var(--app-text)', 
                        fontSize: 15, 
                        padding: '10px 14px', 
                        borderRadius: 8, 
                        outline: 'none',
                        height: 42
                      }}
                    />
                  </Col>
                  <Col xs={24} sm={6} md={4}>
                    <Button
                      type="primary"
                      icon={<Upload size={15} />}
                      onClick={handleSubmit}
                      style={{ 
                        background: 'var(--app-primary)', 
                        color: 'var(--app-on-primary)', 
                        fontWeight: 600, 
                        borderRadius: 8, 
                        height: 42,
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 6,
                        border: 'none'
                      }}
                    >
                      Crawl
                    </Button>
                  </Col>
                </Row>
              )}

              {/* PDF Document Processor */}
              {activeTab === 'pdf' && (
                <Flex vertical gap={16}>
                  {selectedFile ? (
                    <div 
                      style={{ 
                        border: '1px solid var(--app-border)', 
                        borderRadius: 8, 
                        padding: '14px 18px', 
                        background: 'var(--app-surface-muted)' 
                      }}
                    >
                      <Flex align="center" justify="space-between" wrap gap={12}>
                        <Flex align="center" gap={12}>
                          <FileText size={18} color="var(--app-primary)" />
                          <div>
                            <Text style={{ color: 'var(--app-text)', fontSize: 15, display: 'block', fontWeight: 500 }}>
                              {selectedFile.name}
                            </Text>
                            <Text style={{ color: 'var(--app-text-soft)', fontSize: 13 }}>
                              {(selectedFile.size / 1024).toFixed(1)} KB
                            </Text>
                          </div>
                        </Flex>
                        <Button 
                          type="text"
                          icon={<X size={16} />} 
                          onClick={() => setSelectedFile(null)} 
                          style={{ color: 'var(--app-text-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        />
                      </Flex>
                    </div>
                  ) : (
                    <div
                      style={{ 
                        border: '2px dashed var(--app-border)', 
                        borderRadius: 8, 
                        padding: '40px 20px', 
                        display: 'flex', 
                        flexDirection: 'column', 
                        alignItems: 'center', 
                        justifyContent: 'center', 
                        gap: 12, 
                        cursor: 'pointer', 
                        background: 'transparent',
                        transition: 'border-color 0.2s ease'
                      }}
                      onClick={() => document.getElementById('pdf-input')?.click()}
                      className="hover:border-[var(--app-primary)]"
                    >
                      <Upload size={32} color="var(--app-primary)" />
                      <Text style={{ color: 'var(--app-text-muted)', fontSize: 15, textAlign: 'center' }}>
                        Click or drag to upload PDF, TXT, MD, CSV, or JSON files
                      </Text>
                    </div>
                  )}

                  <input
                    id="pdf-input"
                    type="file"
                    accept=".pdf,.txt,.md,.csv,.json"
                    style={{ display: 'none' }}
                    onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                  />

                  <Button
                    type="primary"
                    icon={<Upload size={15} />}
                    onClick={handleSubmit}
                    disabled={!selectedFile}
                    style={{ 
                      background: selectedFile ? 'var(--app-primary)' : 'var(--app-border)', 
                      color: selectedFile ? 'var(--app-on-primary)' : 'var(--app-text-soft)', 
                      fontWeight: 600, 
                      borderRadius: 8, 
                      height: 42,
                      padding: '0 24px',
                      width: 'fit-content',
                      border: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6
                    }}
                  >
                    Upload 
                  </Button>
                </Flex>
              )}

              {/* Raw Text Input Processor */}
              {activeTab === 'text' && (
                <Flex vertical gap={16}>
                  <TextArea
                    value={textContent}
                    onChange={(e) => setTextContent(e.target.value)}
                    placeholder="Paste structural or raw text updates directly into this workspace..."
                    rows={6}
                    style={{ 
                      background: 'var(--app-surface-muted)', 
                      border: '1px solid var(--app-border)', 
                      color: 'var(--app-text)', 
                      fontSize: 15, 
                      borderRadius: 8, 
                      padding: '12px',
                      resize: 'vertical' 
                    }}
                  />
                  <Button
                    type="primary"
                    icon={<Upload size={15} />}
                    onClick={handleSubmit}
                    style={{ 
                      background: 'var(--app-primary)', 
                      color: 'var(--app-on-primary)', 
                      fontWeight: 600, 
                      borderRadius: 8, 
                      height: 42,
                      padding: '0 24px',
                      width: 'fit-content',
                      border: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6
                    }}
                  >
                    Process
                  </Button>
                </Flex>
              )}
            </div>
          </Flex>
        </Card>

        {/* Data Sources Overview Table Section */}
        <Card 
          bordered 
          style={{ 
            background: 'var(--app-surface)', 
            borderColor: 'var(--app-border)', 
            borderRadius: 12,
            overflow: 'hidden'
          }}
          styles={{ body: { padding: 0 } }}
        >
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--app-border)' }}>
            <Text strong style={{ color: 'var(--app-text)', fontSize: 16 }}>
              Data Sources
            </Text>
          </div>
          <div style={{ padding: '60px 20px', textAlign: 'center' }}>
            <Text style={{ color: 'var(--app-text-muted)', fontSize: 15, display: 'block', maxWidth: 400, margin: '0 auto' }}>
              No alternative data streams mounted to this configuration yet. Try submitting context details above.
            </Text>
          </div>
        </Card>

      </Flex>
    </div>
  )
}

// "use client"
// import { Button, Flex, Input, Typography } from 'antd'
// import { useState,useEffect} from 'react'
// import { Globe, FileText, Type, Upload, X } from 'lucide-react'
// import AgentList from "../../components/ui/AgentList";
// import useAxios from '../../hooks/useAxios'
// import type { Agent } from "../../components/ui/type";
// import { useStore } from "../../hooks/useStore";
// import { useRouter } from 'next/navigation'

// const { Text } = Typography
// const { TextArea } = Input

// type AgentListResponse = {
//   data?: {
//     agents?: Agent[];
//   };
// };

// export default function KnowledgeBasePage() {
//   const router = useRouter();
//   const [activeTab, setActiveTab] = useState<'url' | 'pdf' | 'text'>('url')
//   const [url, setUrl] = useState('')
//   const [textContent, setTextContent] = useState('')
//   const [agent, setAgent] = useState<{ id: string; name: string } | null>(null)
//   const [selectedFile, setSelectedFile] = useState<File | null>(null)
//   const setAgentList = useStore((state) => state.setAgentList);
//   const setBotsCache = useStore((state) => state.setBotsCache);
//   const [request] = useAxios<unknown, Record<string, unknown> | FormData>({ endpoint: "KNOWLEDGEBASE" })
//    const [getAgents] = useAxios<AgentListResponse>({ endpoint: "GETAGENTLIST", hideErrorMsg: true });
//   const tabs = [
//     { id: 'url' as const, label: 'URL', icon: <Globe size={14} /> },
//     { id: 'pdf' as const, label: 'PDF', icon: <FileText size={14} /> },
//     { id: 'text' as const, label: 'Text', icon: <Type size={14} /> },
//   ]
//   function mapAgentsToList(agents: Agent[]) {
//       return agents.map((agent) => ({
//         id: agent.id,
//         name: agent.name,
//         status: agent.is_active ? "active" : "draft",
//       }));
//     }
//   // ─── Persistence Logic ──────────────────────────────────────────────────────
//   useEffect(()=>{
//     getAgents(undefined, (payload) => {
//       const agents = payload?.data?.agents ?? [];
//       setBotsCache(agents);
//       setAgentList(mapAgentsToList(agents));
//     });
//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   },[])
//   async function handleSubmit() {
//     if (!agent?.id) {
//       alert("No agent selected")
//       return
//     }

//     if (activeTab === 'url') {

//       request({ data: { agent_id: agent.id, agent_name: agent.name, url }, path: `/${agent.id}/sources/url` })
//       return
//     }

//     if (activeTab === 'pdf') {
//       if (!selectedFile) { console.warn("No file selected"); return }
//       const formData = new FormData()
//       formData.append('agent_id', agent.id)
//       formData.append('agent_name', agent.name)
//       formData.append('file', selectedFile)
//       request({ data: formData, path: `/${agent.id}/sources/pdf`, isFormData: true, transformRequest: [(data: unknown) => data] })
//       return
//     }

//     if (activeTab === 'text') {
//       request({ data: { agent_id: agent.id, agent_name: agent.name, text: textContent }, path: `/${agent.id}/sources` })
//     }
//   }

//   return (
//     <div className="w-full p-10 relative">
//     <Flex vertical gap={20} style={{ background: 'transparent' }}>

//       {/* Header */}
//       <Flex justify="space-between" align="flex-start" wrap>
//         <div>
//           <h1 style={{ color: 'var(--app-text)', fontSize: 38, fontWeight: 700, margin: 0 }}>Knowledge Base</h1>
//           <Text style={{ color: 'var(--app-text-muted)', fontSize: 20, marginTop: 8, display: 'block' }}>
//             Upload and manage data sources for your bots
//           </Text>
//         </div>
//         <div className="pt-5">

//         <Flex gap={12} align="center" wrap>
//           <AgentList
//             selectedId={agent?.id}
//             onChange={(id:string, name:string) => setAgent({ id, name })}
//           />
//           <Button
//             style={{ border: '1px solid var(--app-border)', color: 'var(--app-text-muted)', background: 'var(--app-surface)', borderRadius: 8 }}
//             onClick={() => router.push("/dashboard/graph")}
//           >
//             View Graph
//           </Button>
//         </Flex>
//         </div>
//       </Flex>

//       {/* Adding sources banner */}
//       <div style={{ background: 'var(--app-surface)', border: '1px solid var(--app-border)', borderRadius: 10, padding: '14px 18px' }}>
//         <Flex align="center" gap={16}>
//           <div style={{ width: 36, height: 36, background: 'var(--app-active-bg)', border: '1px solid var(--app-border)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
//             <FileText size={16} color="var(--app-primary)" />
//           </div>
//           <div>
//             <Text style={{ color: 'var(--app-text-muted)', fontSize: 18, display: 'block' }}>
//               Adding sources to:{' '}
//               <span style={{ color: 'var(--app-primary)', fontWeight: 600 }}>{agent?.name ?? 'None selected'}</span>
//             </Text>
//             <Text style={{ color: 'var(--app-text-soft)', fontSize: 15, marginTop: 2, display: 'block' }}>0 sources loaded</Text>
//           </div>
//         </Flex>
//       </div>

//       {/* Upload box */}
//       <div style={{ background: 'var(--app-surface)', border: '1px solid var(--app-border)', borderRadius: 10, padding: 20 }}>
//         <Flex vertical gap={16} wrap>

//           {/* Tabs */}
//           <Flex gap={4} wrap>
//             {tabs.map((tab) => (
//               <button
//                 key={tab.id}
//                 onClick={() => setActiveTab(tab.id)}
//                 style={{
//                   background: activeTab === tab.id ? 'var(--app-primary)' : 'transparent',
//                   color: activeTab === tab.id ? 'var(--app-on-primary)' : 'var(--app-text-muted)',
//                   fontWeight: activeTab === tab.id ? 700 : 400,
//                   borderRadius: 8,
//                   display: 'flex',
//                   alignItems: 'center',
//                   gap: 6,
//                   border: 'none',
//                   cursor: 'pointer',
//                   padding: '6px 14px',
//                   fontSize: 13,
//                 }}
//               >
//                 {tab.icon}
//                 {tab.label}
//               </button>
//             ))}
//           </Flex>

//           {/* URL Tab */}
//           {activeTab === 'url' && (
//             <Flex gap={12} align="center" wrap>
//               <input
//                 type="text"
//                 value={url}
//                 onChange={(e) => setUrl(e.target.value)}
//                 placeholder="https://docs.example.com"
//                 style={{ flex: 1, background: 'var(--app-surface-muted)', border: '1px solid var(--app-border)', color: 'var(--app-text)', fontSize: 16, padding: '10px 14px', borderRadius: 8, outline: 'none' }}
//               />
//               <button
//                 onClick={handleSubmit}
//                 style={{ background: 'var(--app-primary)', color: 'var(--app-on-primary)', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px', fontSize: 16 }}
//               >
//                 <Upload size={14} />
//                 Crawl
//               </button>
//             </Flex>
//           )}

//           {/* PDF Tab */}
//           {activeTab === 'pdf' && (
//             <Flex vertical gap={12} wrap>
//               {selectedFile ? (
//                 <Flex
//                   align="center"
//                   wrap
//                   justify="space-between"
//                   style={{ border: '1px solid var(--app-border)', borderRadius: 10, padding: '12px 16px', background: 'var(--app-surface-muted)' }}
//                 >
//                   <Flex align="center" gap={12}>
//                     <FileText size={16} color="var(--app-primary)" />
//                     <div>
//                       <Text style={{ color: 'var(--app-text)', fontSize: 15, display: 'block' }}>{selectedFile.name}</Text>
//                       <Text style={{ color: 'var(--app-text-soft)', fontSize: 13 }}>{(selectedFile.size / 1024).toFixed(1)} KB</Text>
//                     </div>
//                   </Flex>
//                   <div onClick={() => setSelectedFile(null)} style={{ cursor: 'pointer', color: 'var(--app-text-soft)', display: 'flex' }}>
//                     <X size={14} />
//                   </div>
//                 </Flex>
//               ) : (
//                 <div
//                   style={{ border: '2px dashed var(--app-border)', borderRadius: 10, padding: '48px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12, cursor: 'pointer', background: 'transparent' }}
//                   onClick={() => document.getElementById('pdf-input')?.click()}
//                 >
//                   <Upload size={28} color="var(--app-primary)" />
//                   <Text style={{ color: 'var(--app-text-muted)', fontSize: 16 }}>Click to upload PDF, TXT, MD, CSV, or JSON files</Text>
//                 </div>
//               )}

//               <input
//                 id="pdf-input"
//                 type="file"
//                 accept=".pdf,.txt,.md,.csv,.json"
//                 style={{ display: 'none' }}
//                 onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
//               />

//               <button
//                 onClick={handleSubmit}
//                 disabled={!selectedFile}
//                 style={{ background: selectedFile ? 'var(--app-primary)' : 'var(--app-border)', color: selectedFile ? 'var(--app-on-primary)' : 'var(--app-text-soft)', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: selectedFile ? 'pointer' : 'not-allowed', padding: '10px 18px', width: 'fit-content', fontSize: 16 }}
//               >
//                 <Upload size={14} />
//                 Upload
//               </button>
//             </Flex>
//           )}

//           {/* Text Tab */}
//           {activeTab === 'text' && (
//             <Flex vertical gap={12}>
//               <TextArea
//                 value={textContent}
//                 onChange={(e) => setTextContent(e.target.value)}
//                 placeholder="Paste your text content here..."
//                 rows={5}
//                 style={{ background: 'var(--app-surface-muted)', border: '1px solid var(--app-border)', color: 'var(--app-text)', fontSize: 16, borderRadius: 8, resize: 'vertical' }}
//               />
//               <div>
//                 <button
//                   onClick={handleSubmit}
//                   style={{ background: 'var(--app-primary)', color: 'var(--app-on-primary)', fontWeight: 700, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer', padding: '10px 18px', fontSize: 16 }}
//                 >
//                   <Upload size={14} />
//                   Process
//                 </button>
//               </div>
//             </Flex>
//           )}

//         </Flex>
//       </div>

//       {/* Data Sources */}
//       <div style={{ background: 'var(--app-surface)', border: '1px solid var(--app-border)', borderRadius: 10, overflow: 'hidden' }}>
//         <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--app-border)' }}>
//           <Text strong style={{ color: 'var(--app-text)', fontSize: 16 }}>Data Sources</Text>
//         </div>
//         <div style={{ padding: 40, textAlign: 'center' }}>
//           <Text style={{ color: 'var(--app-text-muted)', fontSize: 16 }}>No sources added yet. Upload URLs, files, or text above.</Text>
//         </div>
//       </div>

//     </Flex>
//   </div>
//   )
// }
