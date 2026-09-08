"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  Button,
  Typography,
  Select,
  Tag,
  Spin,
  App,
  Tooltip,
  Empty,
} from "antd";
import {
  RobotOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  DisconnectOutlined,
  InfoCircleOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import { FaSlack } from "react-icons/fa6";
import { getCookie } from "../../config/cookies";
import { AUTH_COOKIE_KEY, API_BASE_URL } from "../../config/config";

const { Title, Text, Paragraph } = Typography;

// TypeScript Types as specified
export type SlackConnection = {
  agentId: string;
  connected: boolean;
  teamName?: string;
  channelId?: string;
  channelName?: string;
};

export type SlackChannel = {
  id: string;
  name: string;
};

export type Agent = {
  id: string;
  name: string;
  description?: string;
  personality?: string;
  is_active?: boolean;
  total_conversations?: number;
  [key: string]: any;
};

// Auth Header helper function matching project patterns
const getAuthHeaders = (): Record<string, string> => {
  const token = getCookie(AUTH_COOKIE_KEY) || getCookie("AUTH_TOKEN");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

function SlackIntegrationContent() {
  const { message, modal } = App.useApp();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [loadingAgents, setLoadingAgents] = useState<boolean>(true);

  // Store Slack connection info per agent: { [agentId]: SlackConnection }
  const [connections, setConnections] = useState<Record<string, SlackConnection>>({});

  // Store Slack channel options per agent: { [agentId]: SlackChannel[] }
  const [channels, setChannels] = useState<Record<string, SlackChannel[]>>({});

  // Loading state per agent action: { [agentId]: boolean }
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  // Fetch channels for a connected agent
  const fetchSlackChannels = useCallback(
    async (agentId: string, silent = false) => {
      try {
        if (!silent) {
          setActionLoading((prev) => ({ ...prev, [agentId]: true }));
        }

        const res = await fetch(`${API_BASE_URL}/slack/channels?agent_id=${agentId}`, {
          method: "GET",
          headers: getAuthHeaders(),
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: Failed to fetch Slack channels`);
        }

        const data = await res.json();

        // Support multiple backend response structures:
        let channelList: SlackChannel[] = [];
        let teamName = "";
        let selectedChannelId = "";
        let selectedChannelName = "";

        if (Array.isArray(data)) {
          channelList = data;
        } else if (data?.data && Array.isArray(data.data)) {
          channelList = data.data;
        } else if (data?.channels && Array.isArray(data.channels)) {
          channelList = data.channels;
          teamName = data.team_name || data.teamName || "";
          selectedChannelId = data.channel_id || data.channelId || data.selected_channel_id || "";
          selectedChannelName = data.channel_name || data.channelName || "";
        } else if (data?.data?.channels && Array.isArray(data.data.channels)) {
          channelList = data.data.channels;
          teamName = data.data.team_name || data.data.teamName || "";
          selectedChannelId = data.data.channel_id || data.data.channelId || "";
          selectedChannelName = data.data.channel_name || data.data.channelName || "";
        }

        setChannels((prev) => ({ ...prev, [agentId]: channelList }));

        // Mark connection as active if channels loaded successfully
        setConnections((prev) => ({
          ...prev,
          [agentId]: {
            agentId,
            connected: true,
            teamName: teamName || prev[agentId]?.teamName || "Workspace",
            channelId: selectedChannelId || prev[agentId]?.channelId,
            channelName: selectedChannelName || prev[agentId]?.channelName,
          },
        }));
      } catch (err: any) {
        console.error(`Error fetching channels for agent ${agentId}:`, err);
        setConnections((prev) => ({
          ...prev,
          [agentId]: {
            agentId,
            connected: false,
          },
        }));
      } finally {
        setActionLoading((prev) => ({ ...prev, [agentId]: false }));
      }
    },
    []
  );

  // Fetch agents list
  const fetchAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      let res = await fetch(`${API_BASE_URL}/agents`, {
        method: "GET",
        headers: getAuthHeaders(),
      });

      if (!res.ok) {
        const userId = typeof window !== "undefined" ? localStorage.getItem("userId") : null;
        if (userId) {
          res = await fetch(`${API_BASE_URL}/agents/by-user?user_id=${userId}`, {
            method: "GET",
            headers: getAuthHeaders(),
          });
        }
      }

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to fetch agents list`);
      }

      const responseData = await res.json();
      const agentList: Agent[] =
        responseData?.data?.agents ||
        responseData?.agents ||
        (Array.isArray(responseData?.data) ? responseData.data : null) ||
        (Array.isArray(responseData) ? responseData : []);

      setAgents(agentList);

      // Check Slack connection status for each agent
      agentList.forEach((agent) => {
        if (agent.slack_connected || agent.slack_team_name) {
          setConnections((prev) => ({
            ...prev,
            [agent.id]: {
              agentId: agent.id,
              connected: true,
              teamName: agent.slack_team_name || agent.slack_team || "Workspace",
              channelId: agent.slack_channel_id,
              channelName: agent.slack_channel_name,
            },
          }));
          fetchSlackChannels(agent.id, true);
        } else {
          fetchSlackChannels(agent.id, true);
        }
      });
    } catch (err: any) {
      console.error("Error fetching agents:", err);
      message.error(err?.message || "Failed to load agents list. Please try again.");
    } finally {
      setLoadingAgents(false);
    }
  }, [fetchSlackChannels, message]);

  // Check URL query parameters for Slack OAuth return
  useEffect(() => {
    if (typeof window === "undefined") return;

    const searchParams = new URLSearchParams(window.location.search);
    const slackParam = searchParams.get("slack");
    const agentIdParam = searchParams.get("agent_id") || searchParams.get("agentId");

    if (slackParam === "connected") {
      message.success("Slack workspace connected successfully!");
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);

      if (agentIdParam) {
        setConnections((prev) => ({
          ...prev,
          [agentIdParam]: {
            agentId: agentIdParam,
            connected: true,
          },
        }));
        fetchSlackChannels(agentIdParam);
      } else {
        fetchAgents();
      }
    } else if (slackParam === "error") {
      message.error("Failed to connect Slack workspace. Please try again.");
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
    } else {
      fetchAgents();
    }
  }, [fetchAgents, fetchSlackChannels, message]);

  // Connect to Slack button click
  const handleConnectSlack = async (agentId: string) => {
    setActionLoading((prev) => ({ ...prev, [agentId]: true }));
    try {
      const res = await fetch(`${API_BASE_URL}/slack/connect?agent_id=${agentId}`, {
        method: "GET",
        headers: getAuthHeaders(),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Unable to initiate Slack authorization`);
      }

      const data = await res.json();
      const authUrl = data?.authorization_url || data?.data?.authorization_url || data?.url;

      if (authUrl) {
        message.loading("Redirecting to Slack authorization...", 1.5);
        window.location.href = authUrl;
      } else {
        throw new Error("Authorization URL not received from server");
      }
    } catch (err: any) {
      console.error("Connect to Slack error:", err);
      message.error(err?.message || "Failed to initiate Slack connection.");
      setActionLoading((prev) => ({ ...prev, [agentId]: false }));
    }
  };

  // Select Channel dropdown change
  const handleSelectChannel = async (agentId: string, channelId: string, channelOption: any) => {
    const channelName = channelOption?.label || channelOption?.children || "";
    setActionLoading((prev) => ({ ...prev, [agentId]: true }));

    try {
      const res = await fetch(`${API_BASE_URL}/slack/set-channel`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          agent_id: agentId,
          channel_id: channelId,
          channel_name: channelName,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to link Slack channel`);
      }

      setConnections((prev) => ({
        ...prev,
        [agentId]: {
          ...prev[agentId],
          agentId,
          connected: true,
          channelId,
          channelName,
        },
      }));

      message.success("Channel linked successfully");
    } catch (err: any) {
      console.error("Set channel error:", err);
      message.error(err?.message || "Failed to link channel to agent.");
    } finally {
      setActionLoading((prev) => ({ ...prev, [agentId]: false }));
    }
  };

  // Disconnect button click with confirmation modal
  const handleDisconnectSlack = (agentId: string, agentName: string) => {
    modal.confirm({
      title: "Disconnect Slack Integration?",
      icon: <DisconnectOutlined style={{ color: "#ff4d4f" }} />,
      content: (
        <Text className="text-[var(--app-text-soft)]">
          Are you sure you want to disconnect <strong>{agentName}</strong> from your Slack workspace?
          This agent will no longer respond to events in the linked Slack channels.
        </Text>
      ),
      okText: "Disconnect",
      okType: "danger",
      cancelText: "Cancel",
      maskClosable: true,
      centered: true,
      onOk: async () => {
        setActionLoading((prev) => ({ ...prev, [agentId]: true }));
        try {
          const res = await fetch(`${API_BASE_URL}/slack/disconnect?agent_id=${agentId}`, {
            method: "DELETE",
            headers: getAuthHeaders(),
          });

          if (!res.ok) {
            throw new Error(`HTTP ${res.status}: Failed to disconnect Slack workspace`);
          }

          setConnections((prev) => ({
            ...prev,
            [agentId]: {
              agentId,
              connected: false,
              teamName: undefined,
              channelId: undefined,
              channelName: undefined,
            },
          }));

          setChannels((prev) => ({ ...prev, [agentId]: [] }));

          message.success("Disconnected from Slack successfully");
        } catch (err: any) {
          console.error("Disconnect Slack error:", err);
          message.error(err?.message || "Failed to disconnect from Slack.");
        } finally {
          setActionLoading((prev) => ({ ...prev, [agentId]: false }));
        }
      },
    });
  };

  return (
    <div className="w-full flex flex-col gap-8 my-6">
      {/* Header Banner Card with responsive padding & spacing */}
      <Card
        className="overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl shadow-sm mb-2"
        styles={{ body: { padding: "28px 32px" } }}
      >
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
          <div className="flex items-center gap-5 min-w-0 flex-1">
            <div className="w-14 h-14 shrink-0 rounded-2xl bg-[#4A154B]/10 text-[#4A154B] dark:text-[#E01E5A] dark:bg-[#4A154B]/30 flex items-center justify-center text-3xl shadow-sm">
              <FaSlack />
            </div>
            <div className="min-w-0 flex-1 space-y-1">
              <Title level={4} className="!m-0 !text-[var(--app-text)] !font-extrabold tracking-tight">
                Slack Workspace Integration
              </Title>
              <Text className="text-[var(--app-text-soft)] text-sm font-medium block leading-relaxed">
                Connect your AI agents to Slack channels for real-time automated support and query resolution.
              </Text>
            </div>
          </div>

          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchAgents()}
            loading={loadingAgents}
            className="shrink-0 h-10 px-5 rounded-xl border-[var(--app-border)] font-semibold text-[var(--app-text)] hover:!border-[#0fb5a1] hover:!text-[#0fb5a1] transition-all"
          >
            Refresh
          </Button>
        </div>
      </Card>

      {/* Main Agents Grid / Loading / Empty State */}
      {loadingAgents ? (
        <div className="py-20 text-center bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl">
          <Spin size="large" />
          <Text className="block mt-4 text-[var(--app-text-soft)] font-medium">
            Fetching your AI agents...
          </Text>
        </div>
      ) : agents.length === 0 ? (
        <Card className="py-12 bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl text-center">
          <Empty
            description={
              <Text className="text-[var(--app-text-soft)] font-medium">
                No AI agents found for your account. Create an agent first to set up Slack integration.
              </Text>
            }
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
          {agents.map((agent) => {
            const conn = connections[agent.id] || { agentId: agent.id, connected: false };
            const isConnected = !!conn.connected;
            const agentChannels = channels[agent.id] || [];
            const isLoading = !!actionLoading[agent.id];

            return (
              <Card
                key={agent.id}
                className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-3xl transition-all duration-300 hover:shadow-lg hover:border-[#0fb5a1]/40 flex flex-col justify-between"
                styles={{
                  body: {
                    padding: "24px 28px",
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                    justify: "space-between",
                  },
                }}
              >
                {/* Ambient glow accent */}
                <div className="absolute top-0 right-0 w-28 h-28 bg-[#0fb5a1]/5 rounded-bl-[80px] pointer-events-none transition-transform duration-500 group-hover:scale-125" />

                {/* Top Section */}
                <div className="space-y-4">
                  {/* Agent Header - Responsive wrapping layout */}
                  <div className="flex flex-wrap justify-between items-start gap-3 w-full">
                    <div className="flex items-center gap-3.5 min-w-0 flex-1">
                      <div className="w-12 h-12 shrink-0 rounded-2xl bg-[#0fb5a1]/10 text-[#0fb5a1] flex items-center justify-center text-2xl font-bold shadow-inner">
                        <RobotOutlined />
                      </div>
                      <div className="min-w-0 flex-1">
                        <Title
                          level={5}
                          className="!m-0 !text-[var(--app-text)] !font-bold tracking-tight truncate"
                          title={agent.name}
                        >
                          {agent.name}
                        </Title>
                        {agent.personality && (
                          <div className="mt-1 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-[#0fb5a1] shrink-0" />
                            <Text className="text-[11px] font-bold text-[#0fb5a1] uppercase tracking-wider truncate">
                              {agent.personality}
                            </Text>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Connection Status Tag */}
                    <div className="shrink-0">
                      {isConnected ? (
                        <Tag
                          icon={<CheckCircleOutlined />}
                          color="success"
                          className="rounded-full px-3 py-1 text-xs font-semibold !border-emerald-200 !bg-emerald-50 text-emerald-700 dark:!bg-emerald-950/40 dark:!border-emerald-800 dark:!text-emerald-300 m-0"
                        >
                          Connected to {conn.teamName || "Slack"}
                        </Tag>
                      ) : (
                        <Tag
                          color="default"
                          className="rounded-full px-3 py-1 text-xs font-semibold !border-gray-200 !bg-gray-100 text-gray-600 dark:!bg-gray-800 dark:!border-gray-700 dark:!text-gray-400 m-0"
                        >
                          Not Connected
                        </Tag>
                      )}
                    </div>
                  </div>

                  {/* Agent Description */}
                  <Paragraph className="text-[var(--app-text-soft)] text-xs font-normal leading-relaxed line-clamp-2 mt-3 !mb-0">
                    {agent.description || "Multi-agent automation system ready to handle Slack user requests."}
                  </Paragraph>
                </div>

                {/* Bottom Actions Section */}
                <div className="mt-6 pt-5 border-t border-[var(--app-border)] space-y-4">
                  {isConnected ? (
                    <div className="space-y-3">
                      <div>
                        <div className="flex justify-between items-center mb-2">
                          <Text className="text-xs font-bold text-[var(--app-text)]">
                            Linked Slack Channel:
                          </Text>
                          {conn.channelName && (
                            <Text className="text-[11px] font-semibold text-[#0fb5a1] truncate max-w-[140px]">
                              #{conn.channelName}
                            </Text>
                          )}
                        </div>

                        <Select
                          placeholder="Select Slack Channel"
                          value={conn.channelId || undefined}
                          loading={isLoading}
                          disabled={isLoading}
                          onChange={(val, option) => handleSelectChannel(agent.id, val, option)}
                          className="w-full rounded-xl"
                          size="large"
                          options={agentChannels.map((ch) => ({
                            value: ch.id,
                            label: `# ${ch.name}`,
                          }))}
                          notFoundContent={
                            <div className="py-2 text-center text-xs text-[var(--app-text-soft)]">
                              No channels found
                            </div>
                          }
                        />
                      </div>

                      <div className="flex justify-between items-center gap-2 pt-1">
                        <Tooltip title="Reload channels from Slack">
                          <Button
                            type="text"
                            size="small"
                            icon={<SyncOutlined spin={isLoading} />}
                            onClick={() => fetchSlackChannels(agent.id)}
                            disabled={isLoading}
                            className="text-xs text-[var(--app-text-soft)] hover:text-[#0fb5a1] px-1"
                          >
                            Refresh Channels
                          </Button>
                        </Tooltip>

                        <Button
                          danger
                          type="default"
                          icon={<DisconnectOutlined />}
                          loading={isLoading}
                          onClick={() => handleDisconnectSlack(agent.id, agent.name)}
                          className="rounded-xl text-xs font-semibold border-red-200 dark:border-red-900/50 hover:!bg-red-50 dark:hover:!bg-red-950/40"
                        >
                          Disconnect
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 text-xs text-[var(--app-text-soft)]">
                        <InfoCircleOutlined className="text-[#0fb5a1] shrink-0" />
                        <span>Authorize agent to interact inside Slack channels</span>
                      </div>

                      <Button
                        type="primary"
                        icon={<FaSlack className="text-base shrink-0" />}
                        loading={isLoading}
                        onClick={() => handleConnectSlack(agent.id)}
                        className="w-full h-11 rounded-xl !bg-[#0fb5a1] hover:!bg-[#0a8576] !border-none font-bold text-white shadow-sm transition-all active:scale-[0.98] flex items-center justify-center gap-2"
                      >
                        Connect to Slack
                      </Button>
                    </div>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function SlackIntegrationSettings() {
  return (
    <App>
      <SlackIntegrationContent />
    </App>
  );
}
