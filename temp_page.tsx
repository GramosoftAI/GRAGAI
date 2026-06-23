"use client";

import { Flex, Typography, Card, Button, App, Tooltip } from "antd";
import { CopyOutlined, CheckCircleOutlined,} from "@ant-design/icons";
import { useState,useEffect } from "react";
import AgentList from "../../components/ui/AgentList";
import useAxios from "../../hooks/useAxios";
import { useStore } from "../../hooks/useStore";
import type { Agent } from "../../components/ui/type";
import { signIn, useSession } from "next-auth/react";
import { getCookie } from "../../config/cookies";
import Image from "next/image";
import GoogleDriveFolderModal from "./GoogleDriveFolderModal";
import SharePointFolderModal from "./SharePointFolderModal";
import { Modal } from "antd";

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

// interface ChannelCardProps {
//   icon: React.ComponentType;
//   title: string;
//   description: string;
//   status: "active" | "available";
// }
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



// ─── Channel Card Component ───────────────────────────────────────────────────

// function ChannelCard({ icon: Icon, title, description, status }: ChannelCardProps) {
//   const isActive = status === "active";
  
   
//   return (
//     <Card 
//       hoverable
//       className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/5 hover:-translate-y-1"
//       styles={{ body: { padding: '24px sm:32px' } }}
//     >
//       {/* Active Glow Accent */}
//       {isActive && (
//         <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#285d91] to-emerald-500 opacity-70" />
//       )}
      
//       <Flex align="start" justify="space-between" gap={16} className="w-full sm:flex-row flex-col">
//         <Flex align="start" gap={20} className="flex-1">
//           <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0 transition-all duration-300 shadow-sm ${
//             isActive 
//               ? 'bg-[#285d91] text-white' 
//               : 'bg-[var(--app-surface-muted)] text-[var(--app-text-soft)] group-hover:bg-[#285d91]/10 group-hover:text-[#285d91]'
//           }`}>
//             <Icon />
//           </div>
//           <div className="space-y-1">
//             <Title level={4} className="!m-0 !text-[var(--app-text)] !font-bold !text-base tracking-tight group-hover:text-[#285d91] transition-colors">
//               {title}
//             </Title>
//             <Text className="text-[var(--app-text-muted)] text-sm leading-snug block">
//               {description}
//             </Text>
//           </div>
//         </Flex>
        
//         <div className="sm:self-start self-end flex-shrink-0 pt-1">
//           <Badge 
//             status={isActive ? "processing" : "default"} 
//             color={isActive ? "#10b981" : "#64748b"} 
//             text={
//               <Text className={`font-bold uppercase tracking-widest text-[10px] ml-1.5 ${
//                 isActive ? 'text-emerald-500' : 'text-slate-400'
//               }`}>
//                 {status}
//               </Text>
//             } 
//           />
//         </div>
//       </Flex>
//     </Card>
//   );
// }

// ─── Main Content Layout ──────────────────────────────────────────────────────

function IntegrationsContent() {
  const { notification } = App.useApp();
  const { data: session } = useSession() as any;
  const [copied, setCopied] = useState(false);
  const setAgentList = useStore((state) => state.setAgentList);
  const setBotsCache = useStore((state) => state.setBotsCache);
  
  const [agentresp, setAgentresponse] = useState<any>(null);
  const [agent, setAgent] = useState<{ id: string; name: string } | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  
  const [agentkbreq] = useAxios<any>({endpoint:"GET_LISTS", hideErrorMsg:true});
  const [agentkbres, setagentkbres] = useState(""); // KB ID

  // --- Independent State Variables ---
  const [googleStatus, setGoogleStatus] = useState<"Connect" | "Connecting" | "Connected">("Connect");
  const [sharePointStatus, setSharePointStatus] = useState<"Connect" | "Connecting" | "Connected">("Connect");
  
  const [googleModal, setGoogleModal] = useState(false);
  const [sharePointModal, setSharePointModal] = useState(false);

  const [getAgents] = useAxios<AgentListResponse>({ endpoint: "GETAGENTLIST", hideErrorMsg: true });
  const [disconnect] = useAxios<any>({ endpoint: "DISCONNECT" });

  function mapAgentsToList(agents: Agent[]) {
    return agents.map((agent) => ({
      id: agent.id,
      name: agent.name,
      status: agent.is_active ? "active" : "draft",
    }));
  }

  // Fetch Agent List on Mount
  useEffect(() => {
    getAgents(undefined, (payload) => {
      const agents = payload?.data?.agents ?? [];
      setAgentresponse(agents);
      setBotsCache(agents);
      setAgentList(mapAgentsToList(agents));
    });
  }, []);

  // Fetch KB ID when Agent is selected
  useEffect(() => {
    if (agent?.id) {
      agentkbreq({
        data: {
          agent_id: agent.id,
          name: agent.name
        }
      }).then((res: any) => {
        if (res?.data?.kb?.id) {
          setagentkbres(res.data.kb.id);
        }
      }).catch((err: any) => {
        console.error("Error fetching KB:", err);
      });
    } else {
      setagentkbres("");
      setGoogleStatus("Connect");
      setSharePointStatus("Connect");
    }
  }, [agent]);

  // Check Connection Status whenever KB ID changes
  const checkConnection = async () => {
    if (!agent?.id || !agentkbres) return;
    const token = getCookie("AUTH_TOKEN");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/agents/${agent.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      const integrations = data.data?.agent?.connected_integrations || [];
      
      if (integrations.includes("google_drive")) {
        setGoogleStatus("Connected");
      } else {
        setGoogleStatus("Connect");
      }

      if (integrations.includes("sharepoint")) {
        setSharePointStatus("Connected");
      } else {
        setSharePointStatus("Connect");
      }
    } catch (err) {
      console.error("Error checking connection:", err);
    }
  };

  useEffect(() => {
    if (agentkbres) {
      checkConnection();
    }
  }, [agentkbres]);

  // Handle OAuth Redirects for Google Drive and SharePoint
  useEffect(() => {
    const handleOAuthRedirects = async () => {
      if (!session || !agentkbres) return;
      const token = getCookie("AUTH_TOKEN");

      // Check for pending Google registration
      const pendingGoogle = localStorage.getItem("pending_google_register");
      if (pendingGoogle === agentkbres && session.refreshToken) {
        setGoogleStatus("Connecting");
        try {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/knowledge-bases/${agentkbres}/google-drive/register`,
            {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`,
              },
              body: JSON.stringify({
                credentials: {
                  client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
                  client_secret: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_SECRET,
                  refresh_token: session.refreshToken,
                  token_uri: "https://oauth2.googleapis.com/token",
                  primary_admin_email: session.user?.email
                },
                folder_urls: []
              }),
            }
          );
          if (response.ok) {
            setGoogleModal(true);
            setGoogleStatus("Connected"); // Optimistic update
          } else {
            setGoogleStatus("Connect");
          }
        } catch (error) {
          console.error("Google register error:", error);
          setGoogleStatus("Connect");
        } finally {
          localStorage.removeItem("pending_google_register");
        }
      }

      // Check for pending SharePoint registration
      const pendingSharePoint = localStorage.getItem("pending_sharepoint_register");
      if (pendingSharePoint === agentkbres && session.tenantId) {
        setSharePointStatus("Connecting");
        try {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/knowledge-bases/${agentkbres}/sharepoint/register`,
            {
              method: "POST",
              headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                credentials: {
                  client_id: process.env.NEXT_PUBLIC_MS_CLIENT_ID,
                  client_secret: process.env.NEXT_PUBLIC_MS_CLIENT_SECRET,
                  tenant_id: session.tenantId,
                },
                site_urls: ["https://graph.microsoft.com/v1.0/sites/root"],
              }),
            }
          );
          if (response.ok) {
            setSharePointModal(true);
            setSharePointStatus("Connected");
          } else {
            setSharePointStatus("Connect");
          }
        } catch (error) {
          console.error("SharePoint register error:", error);
          setSharePointStatus("Connect");
        } finally {
          localStorage.removeItem("pending_sharepoint_register");
        }
      }
    };

    handleOAuthRedirects();
  }, [session, agentkbres]);

  const scriptCode = `<script src='${process.env.NEXT_PUBLIC_API_BASES_URL}/chat.js'
                      data-agent-id=${agent?.id}
                      data-tenant-id=${agentresp?.[0]?.tenant_id}
                      ></script>`;

  const handleCopy = () => {
    if (!agent?.id) {
      notification.warning({ message: "Select an Agent", description: "Please select an agent before copying the script.", placement: "topRight" });
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = scriptCode;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    setCopied(true);
    notification.success({ message: "Copied to Clipboard", description: "The snippet is ready to be pasted into your web code base.", placement: "topRight" });
    setTimeout(() => setCopied(false), 2000);
  };

  const loadSession = (session: ChatSession) => {
    setAgent({ id: session.agent_id || session.agentId, name: session.title || session.agentName });
  };
  
  const startNewChat = (selectedAgent: { id: string; name: string }) => {
    const newSessionId = `session_${Date.now()}`;
    const newSession: any = {
      id: newSessionId, agentId: selectedAgent.id, agentName: selectedAgent.name, messages: [], updatedAt: Date.now()
    };
    setSessions(prev => [newSession, ...prev]);
    setAgent(selectedAgent);
  };

  // Connect Handlers
  const handleGoogleConnect = () => {
    if (agentkbres) {
      localStorage.setItem("pending_google_register", agentkbres);
    }
    signIn("google");
  };

  const handleSharePointConnect = () => {
    if (agentkbres) {
      localStorage.setItem("pending_sharepoint_register", agentkbres);
    }
    signIn("azure-ad");
  };

  // Disconnect Handlers
  const handleGoogleDisconnect = () => {
    disconnect({ path: `${agentkbres}` })
      .then((res: any) => {
        if (res.ok) {
          setGoogleStatus("Connect");
          checkConnection();
        }
      })
      .catch((err: any) => console.log(err));
  };

  const handleSharePointDisconnect = () => {
    disconnect({ path: `${agentkbres}` })
      .then((res: any) => {
        if (res.ok) {
          setSharePointStatus("Connect");
          checkConnection();
        }
      })
      .catch((err: any) => console.log(err));
  };

  const showGoogleDisconnectConfirm = () => {
    Modal.confirm({
      title: "Disconnect Google Drive?",
      content: "Are you sure you want to disconnect Google Drive?",
      okText: "Disconnect",
      cancelText: "Cancel",
      okButtonProps: { danger: true },
      onOk() { handleGoogleDisconnect(); },
    });
  };

  const showSharePointDisconnectConfirm = () => {
    Modal.confirm({
      title: "Disconnect SharePoint?",
      content: "Are you sure you want to disconnect SharePoint?",
      okText: "Disconnect",
      cancelText: "Cancel",
      okButtonProps: { danger: true },
      onOk() { handleSharePointDisconnect(); },
    });
  };

  return (
    <>
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
                  Add this snippet to your website <code className="bg-[var(--app-surface-muted)] px-1 py-0.5 rounded text-xs">&lt;body&gt;</code> element to initialize the chat instance.
                </Text>
              </div>
              <div className="scale-90 md:scale-100 origin-right w-full sm:w-auto !h-12 !px-6 ">
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
                  <span className="text-emerald-500">{`${agentresp?.[0]?.tenant_id}`}</span>
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
            {/* Google Drive Card */}
            <Card 
            hoverable
            className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/5 hover:-translate-y-1"
            styles={{ body: { padding: '24px sm:32px' } }}
          >
            <div className=" p-4  flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Image
                    src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png"
                    alt="Google Drive"
                    width={40}
                    height={40}
                  />
                  <div>
                    <h2 className="font-semibold">
                      Google Drive
                    </h2>
                    <p className="text-sm text-gray-500">
                      Files, photos, shared documents
                    </p>
                  </div>
                </div>
            <Tooltip title={!agent?.id ? "You want to select the agent" : ""}>
              {googleStatus === "Connected" ? (
                <Flex gap={2}>
                 <button
                    onClick={() => showGoogleDisconnectConfirm()}
                    style={{ cursor: "pointer" }}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                  >
                    Connected
                 </button>
                 <button
                    onClick={() => setGoogleModal(true)}
                    style={{ cursor: "pointer" }}
                    disabled={!agent?.id}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                  >
                    +
                 </button>
                </Flex>
              ) : (
                <button
                  onClick={handleGoogleConnect}
                  style={{ cursor: "pointer" }}
                  disabled={!agent?.id || googleStatus === "Connecting"}
                  className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                >
                  {googleStatus}
                </button>
              )}                  
            </Tooltip>
            </div>
          </Card>

          {/* SharePoint Card */}
          <Card 
            hoverable
            className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl transition-all duration-300 hover:shadow-xl hover:shadow-blue-900/5 hover:-translate-y-1"
            styles={{ body: { padding: '24px sm:32px' } }}
          >
            <div className=" p-4  flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Image
                      src="https://img.icons8.com/color/96/microsoft-sharepoint-2019.png"
                      alt="SharePoint"
                      width={40}
                      height={40}
                    />
                  <div>
                    <h2 className="font-semibold">
                      SharePoint
                    </h2>
                    <p className="text-sm text-gray-500">
                      Files, photos, shared documents
                    </p>
                  </div>
                </div>   
              <Tooltip title={!agent?.id ? "You want to select the agent" : ""}>
                {sharePointStatus === "Connected" ? (
                  <Flex gap={2}>
                    <button
                      onClick={() => showSharePointDisconnectConfirm()}
                      style={{ cursor: "pointer" }}
                      className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                    >
                      Connected
                    </button>
                    <button
                      onClick={() => setSharePointModal(true)}
                      style={{ cursor: "pointer" }}
                      disabled={!agent?.id}
                      className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                    >
                      +
                    </button>
                  </Flex>
                ) : (
                  <button
                    onClick={handleSharePointConnect}
                    disabled={!agent?.id || sharePointStatus === "Connecting"}
                    style={{ cursor: "pointer" }}
                    className="bg-purple-500 text-white px-4 py-2 rounded-lg"
                  >
                    {sharePointStatus}
                  </button>
                )}
              </Tooltip>               
            </div>
          </Card>
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
      <GoogleDriveFolderModal
        open={googleModal}
        kbId={agentkbres}
        token={getCookie("AUTH_TOKEN") || ""}
        onClose={() => setGoogleModal(false)}
        onSuccess={() => {
          setGoogleStatus("Connected");
          setGoogleModal(false);
          checkConnection();
        }}
        session={session?.user?.email}
      />
      <SharePointFolderModal
        open={sharePointModal}
        kbId={agentkbres}
        token={getCookie("AUTH_TOKEN") || ""}
        onClose={() => setSharePointModal(false)}
        onSuccess={() => {
          setSharePointStatus("Connected");
          setSharePointModal(false);
          checkConnection();
        }}
        session={session?.user?.email}
      />
    </>
  );
}
\n\nexport default function IntegrationsPage() {
      return (
        <App>
          <IntegrationsContent />
        </App>
      );
    }
