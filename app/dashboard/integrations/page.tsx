"use client";

import { Flex, Typography, Card, Badge, Button, App, Tooltip } from "antd";
import { 
  GlobalOutlined, SlackOutlined, 
  CodeOutlined, CopyOutlined, CheckCircleOutlined,
  // ArrowRightOutlined
} from "@ant-design/icons";
import { useState,useEffect } from "react";
import { FaWhatsapp } from "react-icons/fa";
import AgentList from "../../components/ui/AgentList";
import useAxios from "../../hooks/useAxios";
import { useStore } from "../../hooks/useStore";
import type { Agent } from "../../components/ui/type";


const { Title, Text } = Typography;

// ─── Types ──────────────────────────────────────────────────────────────────
type Message = {
  role: "user" | "assistant";
  content: string;
  confidence?: number;
  nodes?: number;
  timestamp?: string;
  message_count?: number;
};

interface ChannelCardProps {
  icon: React.ComponentType;
  title: string;
  description: string;
  status: "active" | "available";
}
type AgentListResponse = {
  data?: {
    agents?: Agent[];
  };
};
type ChatSession = {
  id: string;
  agentId: string;
  agentName: string;
  messages: Message[];
  updatedAt: number;
  agent_id: string;
  title: string;
  message_count: number;
  is_active: boolean;
  last_message_at: string;
  created_at: string;
};
// type Agents = { id: string; name: string } | null;
// ─── Channel Card Component ───────────────────────────────────────────────────

function ChannelCard({ icon: Icon, title, description, status }: ChannelCardProps) {
  const isActive = status === "active";
  
   
  return (
    <Card 
      hoverable
      className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/5 hover:-translate-y-1"
      styles={{ body: { padding: '24px sm:32px' } }}
    >
      {/* Active Glow Accent */}
      {isActive && (
        <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#285d91] to-emerald-500 opacity-70" />
      )}
      
      <Flex align="start" justify="space-between" gap={16} className="w-full sm:flex-row flex-col">
        <Flex align="start" gap={20} className="flex-1">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0 transition-all duration-300 shadow-sm ${
            isActive 
              ? 'bg-[#285d91] text-white' 
              : 'bg-[var(--app-surface-muted)] text-[var(--app-text-soft)] group-hover:bg-[#285d91]/10 group-hover:text-[#285d91]'
          }`}>
            <Icon />
          </div>
          <div className="space-y-1">
            <Title level={4} className="!m-0 !text-[var(--app-text)] !font-bold !text-base tracking-tight group-hover:text-[#285d91] transition-colors">
              {title}
            </Title>
            <Text className="text-[var(--app-text-muted)] text-sm leading-snug block">
              {description}
            </Text>
          </div>
        </Flex>
        
        <div className="sm:self-start self-end flex-shrink-0 pt-1">
          <Badge 
            status={isActive ? "processing" : "default"} 
            color={isActive ? "#10b981" : "#64748b"} 
            text={
              <Text className={`font-bold uppercase tracking-widest text-[10px] ml-1.5 ${
                isActive ? 'text-emerald-500' : 'text-slate-400'
              }`}>
                {status}
              </Text>
            } 
          />
        </div>
      </Flex>
    </Card>
  );
}

// ─── Main Content Layout ──────────────────────────────────────────────────────

function IntegrationsContent() {
  const { notification } = App.useApp();
  const [copied, setCopied] = useState(false);
   const setAgentList = useStore((state) => state.setAgentList);
    const setBotsCache = useStore((state) => state.setBotsCache);
  const [agentresp,setAgentresponse] = useState<any>(null)
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null);
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [getAgents] = useAxios<AgentListResponse>({ endpoint: "GETAGENTLIST", hideErrorMsg: true });
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
        setAgentresponse(agents)
        setBotsCache(agents);
        setAgentList(mapAgentsToList(agents));
      });
       // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
  // const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
    // const [messages, setMessages] = useState<any>([]);
  const scriptCode = `<script src= '${process.env.NEXT_PUBLIC_API_BASES_URL}/chat.js'
                      data-agent-id=${agent?.id}
                      data-tenant-id=${agentresp?.[0].tenant_id}
                      >
                      </script>`;

  // const handleCopy = () => {
  //   navigator.clipboard.writeText(scriptCode);
  //   setCopied(true);
  //   notification.success({
  //     message: 'Copied to Clipboard',
  //     description: 'The snippet is ready to be pasted into your web code base.',
  //     placement: 'topRight'
  //   });
  //   setTimeout(() => setCopied(false), 2000);
  // };
  const handleCopy = () => {
  const textarea = document.createElement("textarea");
  textarea.value = scriptCode;

  document.body.appendChild(textarea);
  textarea.select();

  document.execCommand("copy");

  document.body.removeChild(textarea);

  setCopied(true);

  notification.success({
    message: "Copied to Clipboard",
    description: "The snippet is ready to be pasted into your web code base.",
    placement: "topRight",
  });

  setTimeout(() => setCopied(false), 2000);
};
   const loadSession = (session: ChatSession) => {
    // setCurrentSessionId(session.id);
    
    // Safely map messages even if session.messages is undefined or empty
    // const mappedMessages = (session.messages || []).map((msg: any) => ({
    //   role: msg.role,
    //   content: msg.content,
    //   timestamp: msg.created_at 
    //     ? new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    //     : new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    // }));

    // setMessages(mappedMessages);
    // Dynamic matching for custom parameters
    setAgent({ 
      id: session.agent_id || session.agentId, 
      name: session.title || session.agentName 
    });
  };
  const startNewChat = (selectedAgent: { id: string; name: string }) => {
    const newSessionId = `session_${Date.now()}`;
    const newSession: any = {
      id: newSessionId,
      agentId: selectedAgent.id,
      agentName: selectedAgent.name,
      messages: [],
      updatedAt: Date.now()
    };
    setSessions(prev => [newSession, ...prev]);
    // setCurrentSessionId(newSessionId);
    // setMessages([]);
    setAgent(selectedAgent);
  };
  return (
    <div className="w-full max-w-7xl mx-auto p-3 md:p-10 animate-in fade-in duration-500">
      <Flex vertical gap={40}>
        
        {/* Header Section */}
        <div className="space-y-3 max-w-3xl">
          <Title level={1} className="!m-0 !text-[var(--app-text)] !font-extrabold !text-3xl md:!text-5xl tracking-tight">
            Omnichannel Integrations
          </Title>
          <Text className="text-[var(--app-text-muted)] text-base md:text-lg block leading-relaxed">
            Deploy your cognitive AI agents across every customer touchpoint with seamless integration hooks.
          </Text>
        </div>

        {/* Embed Script Section */}
        <Card 
          className="bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl shadow-md overflow-hidden"
          styles={{ body: { padding: '24px md:40px' } }}
        >
          <Flex vertical gap={24}>
            <Flex justify="space-between" align="start" wrap="wrap" gap={16}>
              <div className="space-y-1">
                <Title level={3} className="!m-0 !text-[var(--app-text)] !font-bold !text-xl tracking-tight">
                  Embed Script
                </Title>
                <Text className="text-[var(--app-text-soft)] text-xs font-medium uppercase tracking-wider block">
                  Add this snippet to your website <code className="bg-[var(--app-surface-muted)] px-1 py-0.5 rounded text-xs">&lt;head&gt;</code> element to initialize the chat instance.
                </Text>
              </div>
              <div className="scale-90 md:scale-100 origin-right">
                              <AgentList
                                selectedId={agent?.id}
                                onChange={(id: string, name: string) => {
                                  const existing = sessions.find(s => s.agentId === id);
                                  if (existing) loadSession(existing);
                                  else startNewChat({ id, name });
                                }}
                              />
                            </div>
              <Tooltip title={copied ? "Copied!" : "Copy Script"}>
                <Button 
                  type="primary" 
                  size="large" 
                  icon={copied ? <CheckCircleOutlined /> : <CopyOutlined />}
                  onClick={handleCopy}
                  className="w-full sm:w-auto !h-12 !px-6 !rounded-xl !bg-[#285d91] !border-none !font-semibold transition-transform active:scale-95 flex items-center justify-center gap-2"
                >
                  {copied ? "Copied" : "Copy Code"}
                </Button>
              </Tooltip>
            </Flex>

            {/* Code Block Window */}
            <div className="relative group rounded-2xl border border-[var(--app-border)] bg-[var(--app-surface-muted)] overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--app-border)] bg-[var(--app-surface)]/50">
                <div className="flex gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-red-400/70" />
                  <span className="w-3 h-3 rounded-full bg-amber-400/70" />
                  <span className="w-3 h-3 rounded-full bg-emerald-400/70" />
                </div>
                <Text className="text-[10px] font-bold uppercase tracking-widest text-slate-400">HTML</Text>
              </div>
              
              <pre className="p-5 md:p-6 overflow-x-auto custom-scrollbar m-0">
                <code className="text-[var(--app-text)] font-mono text-xs md:text-sm leading-relaxed block whitespace-pre">
                  <span className="text-[#285d91] opacity-80">{"<script "}</span>
                  <span className="text-[#3b82f6]">src =</span>
                  <span className="text-emerald-500">{`'${process.env.NEXT_PUBLIC_API_BASES_URL}/chat.js'`}</span>
                  {"\n  "}
                  <span className="text-[#3b82f6]">data-agent-id =</span>
                  <span className="text-emerald-500">{`${agent?.id}`}</span>
                  {"\n  "}
                  <span className="text-[#3b82f6]">data-tenant-id =</span>
                  <span className="text-emerald-500">{`${agentresp?.[0].tenant_id}`}</span>
                  {/* <span className="text-[#3b82f6]">data-theme</span>
                  <span className="text-emerald-500">dark</span> */}
                  <span className="text-[#285d91] opacity-80">{">"}</span>
                  <span className="text-[#285d91] opacity-80">{"</script>"}</span>
                </code>
              </pre>
            </div>
          </Flex>
        </Card>
        {/* Integration Grid */}
        <Flex vertical gap={16}>
          <Title level={5} className="!m-0 !text-[var(--app-text-soft)] !font-bold uppercase tracking-widest text-xs">
            Available Channels
          </Title>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChannelCard 
              icon={GlobalOutlined}
              title="Website Widget"
              description="High-performance, configurable asynchronous embedded interface."
              status="active"
            />
            <ChannelCard 
              icon={SlackOutlined}
              title="Slack Workspace"
              description="Sync natural-language agents directly to internal enterprise workflows."
              status="available"
            />
            <ChannelCard 
              icon={FaWhatsapp}
              title="WhatsApp Business"
              description="Deploy continuous agent support loops running directly via WhatsApp API."
              status="available"
            />
            <ChannelCard 
              icon={CodeOutlined}
              title="REST API"
              description="Expose neural inference layers via lightweight program hooks."
              status="active"
            />
          </div>
        </Flex>

        {/* Ecosystem Banner */}
        <div className="p-8 md:p-12 bg-gradient-to-br from-[#285d91] via-[#204e7c] to-[#153a5e] rounded-3xl text-white shadow-lg overflow-hidden relative">
          <div className="absolute -top-24 -right-24 w-72 h-72 bg-blue-400/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-emerald-400/5 rounded-full blur-3xl pointer-events-none" />
          
          <Flex justify="space-between" align="center" className="w-full flex-col md:flex-row gap-6 relative z-10">
            <div className="space-y-1.5 text-center md:text-left max-w-xl">
              <Title level={3} className="!m-0 !text-white !font-bold !text-xl md:!text-2xl tracking-tight">
                Need a Custom Connection?
              </Title>
              <Text className="text-blue-100 text-sm md:text-base block font-normal leading-relaxed">
                Our core architects design personalized system schemas and custom API loops built for scaled architectures.
              </Text>
            </div>
            <Button 
              size="large" 
              // icon={<ArrowRightOutlined />}
              className="w-full md:w-auto !h-12 !px-8 !rounded-xl !bg-white !text-[#285d91] !border-none !font-semibold transition-transform active:scale-95 flex items-center justify-center flex-row-reverse gap-2"
            >
              Contact Support
            </Button>
          </Flex>
        </div>
        
      </Flex>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--app-border, #e2e8f0);
          border-radius: 99px;
        }
      `}</style>
    </div>
  );
}

export default function IntegrationsPage() {
  return (
    <App>
      <IntegrationsContent />
    </App>
  );
}


// "use client";

// import { Flex, Typography, Card, Row, Col, Badge, Button, App, Tooltip } from "antd";
// import { 
//   GlobalOutlined, SlackOutlined, MessageOutlined, 
//   CodeOutlined, CopyOutlined, CheckCircleOutlined,
//   ThunderboltOutlined, ShareAltOutlined
// } from "@ant-design/icons";
// import { useState } from "react";
// import { FaWhatsapp } from "react-icons/fa";

// const { Title, Text } = Typography;

// // ─── Channel Card Component ───────────────────────────────────────────────────

// function ChannelCard({ 
//   icon: Icon, 
//   title, 
//   description, 
//   status, 
//   type = "default" 
// }: { 
//   icon: any; 
//   title: string; 
//   description: string; 
//   status: "active" | "available";
//   type?: "default" | "whatsapp";
// }) {
//   const isActive = status === "active";
  
//   return (
//     <Card 
//       hoverable
//       className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-[32px] transition-all duration-500 hover:shadow-[0_20px_50px_rgba(40,93,145,0.06)] hover:-translate-y-1"
//       styles={{ body: { padding: 32 } }}
//     >
//       <Flex align="center" justify="space-between" gap={20}>
//         <Flex align="center" gap={20}>
//           <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl transition-all duration-500 shadow-sm ${
//             isActive ? 'bg-[#285d91] text-white shadow-blue-900/20' : 'bg-[var(--app-surface-muted)] text-[var(--app-text-soft)] group-hover:bg-[#285d91]/5 group-hover:text-[#285d91]'
//           }`}>
//             <Icon />
//           </div>
//           <div>
//             <Title level={4} className="!m-0 !text-[var(--app-text)] !font-black !text-lg tracking-tight">
//               {title}
//             </Title>
//             <Text className="text-[var(--app-text-muted)] font-bold text-xs mt-1 block">
//               {description}
//             </Text>
//           </div>
//         </Flex>
//         <div className="flex-shrink-0">
//           <Badge 
//             status={isActive ? "processing" : "default"} 
//             color={isActive ? "#10b981" : "#94a3b8"} 
//             text={
//               <Text className={`font-black uppercase tracking-[0.2em] text-[10px] ml-1 whitespace-nowrap ${isActive ? 'text-emerald-500' : 'text-slate-400 opacity-50'}`}>
//                 {status}
//               </Text>
//             } 
//           />
//         </div>
//       </Flex>
//     </Card>
//   );
// }

// // ─── Main Page ────────────────────────────────────────────────────────────────

// export default function IntegrationsPage() {
//   const { notification } = App.useApp();
//   const [copied, setCopied] = useState(false);
//   const scriptCode = `<script src="https://graphmind.ai/widget.js"
//   data-bot-id="bot_abc123"
//   data-theme="dark">
// </script>`;

//   const handleCopy = () => {
//     navigator.clipboard.writeText(scriptCode);
//     setCopied(true);
//     notification.success({
//       title: 'Copied!',
//       description: 'The deployment script has been copied to your clipboard.',
//       className: "custom-toast-success"
//     });
//     setTimeout(() => setCopied(false), 2000);
//   };

//   return (
//     <div className="w-full pb-20 animate-in fade-in duration-1000">
//       <Flex vertical gap={48}>
//         {/* Header Section */}
//         <Flex vertical gap={12}>
//           <Title level={1} className="!m-0 !text-[var(--app-text)] !font-black !text-4xl md:!text-5xl tracking-tighter">
//             Omnichannel Integrations
//           </Title>
//           <Text className="text-[var(--app-text-muted)] font-semibold text-lg max-w-2xl leading-relaxed">
//             Deploy your cognitive AI agents across every customer touchpoint with seamless integration hooks.
//           </Text>
//         </Flex>

//         {/* Embed Script Card */}
//         <Card 
//           className="bg-[var(--app-surface)] border border-[var(--app-border)] rounded-[40px] shadow-[0_30px_60px_rgba(40,93,145,0.05)] overflow-hidden"
//           styles={{ body: { padding: 48 } }}
//         >
//           <Flex vertical gap={32}>
//             <Flex justify="space-between" align="center">
//               <div>
//                 <Title level={3} className="!m-0 !text-[var(--app-text)] !font-black tracking-tight">
//                   Embed Script
//                 </Title>
//                 <Text className="text-[var(--app-text-soft)] font-bold text-xs uppercase tracking-widest mt-2 block">
//                   Add this to your website's HEAD tag to enable the neural chat widget
//                 </Text>
//               </div>
//               <Tooltip title={copied ? "Copied!" : "Copy Script"}>
//                 <Button 
//                   type="primary" 
//                   size="large" 
//                   icon={copied ? <CheckCircleOutlined /> : <CopyOutlined />}
//                   onClick={handleCopy}
//                   className="!h-14 !px-8 !rounded-2xl !bg-[#285d91] !border-none !font-black !uppercase !tracking-widest shadow-xl shadow-blue-900/10 hover:!scale-105 transition-all"
//                 >
//                   {copied ? "Copied" : "Copy Source"}
//                 </Button>
//               </Tooltip>
//             </Flex>

//             <div className="relative group">
//               <div className="absolute inset-0 bg-gradient-to-br from-[#285d91]/5 to-transparent rounded-[24px] pointer-events-none" />
//               <pre className="p-8 bg-[var(--app-surface-muted)] border border-[var(--app-border)] rounded-[24px] overflow-x-auto custom-scrollbar">
//                 <code className="text-[var(--app-text)] font-mono text-sm leading-relaxed block">
//                   <span className="text-[#285d91] opacity-70">{"<script "}</span>
//                   <span className="text-[#285d91]">src</span>
//                   <span className="text-emerald-500">="https://graphmind.ai/widget.js"</span>
//                   <br />
//                   <span className="ml-2 text-[#285d91]">data-bot-id</span>
//                   <span className="text-emerald-500">="bot_abc123"</span>
//                   <br />
//                   <span className="ml-2 text-[#285d91]">data-theme</span>
//                   <span className="text-emerald-500">="dark"</span>
//                   <span className="text-[#285d91] opacity-70">{">"}</span>
//                   <br />
//                   <span className="text-[#285d91] opacity-70">{"</script>"}</span>
//                 </code>
//               </pre>
//               <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
//                 <Badge status="processing" color="#285d91" text={<Text className="text-[8px] font-black uppercase text-[#285d91]">V1.0.4 Stable</Text>} />
//               </div>
//             </div>
//           </Flex>
//         </Card>

//         {/* Integration Grid */}
//         <Flex vertical gap={24}>
//           <Title level={4} className="!m-0 !text-[var(--app-text)] !font-black uppercase tracking-widest text-xs opacity-50">
//             Available Channels
//           </Title>
//           <Row gutter={[32, 32]}>
//             <Col xs={24} lg={12}>
//               <ChannelCard 
//                 icon={GlobalOutlined}
//                 title="Website Widget"
//                 description="High-performance embeddable chat interface"
//                 status="active"
//               />
//             </Col>
//             <Col xs={24} lg={12}>
//               <ChannelCard 
//                 icon={SlackOutlined}
//                 title="Slack Workspace"
//                 description="Connect AI agents to your internal Slack teams"
//                 status="available"
//               />
//             </Col>
//             <Col xs={24} lg={12}>
//               <ChannelCard 
//                 icon={FaWhatsapp}
//                 title="WhatsApp Business"
//                 description="Reach users directly via WhatsApp Business API"
//                 status="available"
//                 type="whatsapp"
//               />
//             </Col>
//             <Col xs={24} lg={12}>
//               <ChannelCard 
//                 icon={CodeOutlined}
//                 title="REST API"
//                 description="Full access to neural inference via API hooks"
//                 status="active"
//               />
//             </Col>
//           </Row>
//         </Flex>

//         {/* Ecosystem Callout */}
//         <div className="p-10 bg-gradient-to-r from-[#285d91] to-[#1d4d7c] rounded-[40px] text-white shadow-2xl shadow-blue-900/20 overflow-hidden relative">
//           <div className="absolute top-[-50%] right-[-10%] w-[300px] h-[300px] bg-white/10 rounded-full blur-[80px]" />
//           <Flex justify="space-between" align="center" wrap="wrap" gap={32} className="relative z-10">
//             <Flex vertical gap={8}>
//               <Title level={3} className="!m-0 !text-white !font-black tracking-tighter">Need a Custom Link?</Title>
//               <Text className="text-white/70 font-bold">Our architects can help you build bespoke API pipelines for your enterprise ecosystem.</Text>
//             </Flex>
//             <Button 
//               size="large" 
//               className="!h-14 !px-10 !rounded-2xl !bg-white !text-[#285d91] !border-none !font-black !uppercase !tracking-widest hover:!scale-105 transition-all"
//             >
//               Contact Support
//             </Button>
//           </Flex>
//         </div>
//       </Flex>

//       <style jsx global>{`
//         .custom-scrollbar::-webkit-scrollbar {
//           height: 6px;
//         }
//         .custom-scrollbar::-webkit-scrollbar-track {
//           background: transparent;
//         }
//         .custom-scrollbar::-webkit-scrollbar-thumb {
//           background: var(--app-border);
//           border-radius: 10px;
//         }
//       `}</style>
//     </div>
//   );
// }
