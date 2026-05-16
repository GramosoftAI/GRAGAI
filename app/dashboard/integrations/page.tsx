"use client";

import { Flex, Typography, Card, Row, Col, Badge, Button, App, Tooltip } from "antd";
import { 
  GlobalOutlined, SlackOutlined, MessageOutlined, 
  CodeOutlined, CopyOutlined, CheckCircleOutlined,
  ThunderboltOutlined, ShareAltOutlined
} from "@ant-design/icons";
import { useState } from "react";
import { FaWhatsapp } from "react-icons/fa";

const { Title, Text } = Typography;

// ─── Channel Card Component ───────────────────────────────────────────────────

function ChannelCard({ 
  icon: Icon, 
  title, 
  description, 
  status, 
  type = "default" 
}: { 
  icon: any; 
  title: string; 
  description: string; 
  status: "active" | "available";
  type?: "default" | "whatsapp";
}) {
  const isActive = status === "active";
  
  return (
    <Card 
      hoverable
      className="group relative overflow-hidden bg-[var(--app-surface)] border border-[var(--app-border)] rounded-[32px] transition-all duration-500 hover:shadow-[0_20px_50px_rgba(40,93,145,0.06)] hover:-translate-y-1"
      styles={{ body: { padding: 32 } }}
    >
      <Flex align="center" justify="space-between" gap={20}>
        <Flex align="center" gap={20}>
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl transition-all duration-500 shadow-sm ${
            isActive ? 'bg-[#285d91] text-white shadow-blue-900/20' : 'bg-[var(--app-surface-muted)] text-[var(--app-text-soft)] group-hover:bg-[#285d91]/5 group-hover:text-[#285d91]'
          }`}>
            <Icon />
          </div>
          <div>
            <Title level={4} className="!m-0 !text-[var(--app-text)] !font-black !text-lg tracking-tight">
              {title}
            </Title>
            <Text className="text-[var(--app-text-muted)] font-bold text-xs mt-1 block">
              {description}
            </Text>
          </div>
        </Flex>
        <div className="flex-shrink-0">
          <Badge 
            status={isActive ? "processing" : "default"} 
            color={isActive ? "#10b981" : "#94a3b8"} 
            text={
              <Text className={`font-black uppercase tracking-[0.2em] text-[10px] ml-1 whitespace-nowrap ${isActive ? 'text-emerald-500' : 'text-slate-400 opacity-50'}`}>
                {status}
              </Text>
            } 
          />
        </div>
      </Flex>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const { notification } = App.useApp();
  const [copied, setCopied] = useState(false);
  const scriptCode = `<script src="https://graphmind.ai/widget.js"
  data-bot-id="bot_abc123"
  data-theme="dark">
</script>`;

  const handleCopy = () => {
    navigator.clipboard.writeText(scriptCode);
    setCopied(true);
    notification.success({
      title: 'Copied!',
      description: 'The deployment script has been copied to your clipboard.',
      className: "custom-toast-success"
    });
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full pb-20 animate-in fade-in duration-1000">
      <Flex vertical gap={48}>
        {/* Header Section */}
        <Flex vertical gap={12}>
          <Title level={1} className="!m-0 !text-[var(--app-text)] !font-black !text-4xl md:!text-5xl tracking-tighter">
            Omnichannel Integrations
          </Title>
          <Text className="text-[var(--app-text-muted)] font-semibold text-lg max-w-2xl leading-relaxed">
            Deploy your cognitive AI agents across every customer touchpoint with seamless integration hooks.
          </Text>
        </Flex>

        {/* Embed Script Card */}
        <Card 
          className="bg-[var(--app-surface)] border border-[var(--app-border)] rounded-[40px] shadow-[0_30px_60px_rgba(40,93,145,0.05)] overflow-hidden"
          styles={{ body: { padding: 48 } }}
        >
          <Flex vertical gap={32}>
            <Flex justify="space-between" align="center">
              <div>
                <Title level={3} className="!m-0 !text-[var(--app-text)] !font-black tracking-tight">
                  Embed Script
                </Title>
                <Text className="text-[var(--app-text-soft)] font-bold text-xs uppercase tracking-widest mt-2 block">
                  Add this to your website's HEAD tag to enable the neural chat widget
                </Text>
              </div>
              <Tooltip title={copied ? "Copied!" : "Copy Script"}>
                <Button 
                  type="primary" 
                  size="large" 
                  icon={copied ? <CheckCircleOutlined /> : <CopyOutlined />}
                  onClick={handleCopy}
                  className="!h-14 !px-8 !rounded-2xl !bg-[#285d91] !border-none !font-black !uppercase !tracking-widest shadow-xl shadow-blue-900/10 hover:!scale-105 transition-all"
                >
                  {copied ? "Copied" : "Copy Source"}
                </Button>
              </Tooltip>
            </Flex>

            <div className="relative group">
              <div className="absolute inset-0 bg-gradient-to-br from-[#285d91]/5 to-transparent rounded-[24px] pointer-events-none" />
              <pre className="p-8 bg-[var(--app-surface-muted)] border border-[var(--app-border)] rounded-[24px] overflow-x-auto custom-scrollbar">
                <code className="text-[var(--app-text)] font-mono text-sm leading-relaxed block">
                  <span className="text-[#285d91] opacity-70">{"<script "}</span>
                  <span className="text-[#285d91]">src</span>
                  <span className="text-emerald-500">="https://graphmind.ai/widget.js"</span>
                  <br />
                  <span className="ml-2 text-[#285d91]">data-bot-id</span>
                  <span className="text-emerald-500">="bot_abc123"</span>
                  <br />
                  <span className="ml-2 text-[#285d91]">data-theme</span>
                  <span className="text-emerald-500">="dark"</span>
                  <span className="text-[#285d91] opacity-70">{">"}</span>
                  <br />
                  <span className="text-[#285d91] opacity-70">{"</script>"}</span>
                </code>
              </pre>
              <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <Badge status="processing" color="#285d91" text={<Text className="text-[8px] font-black uppercase text-[#285d91]">V1.0.4 Stable</Text>} />
              </div>
            </div>
          </Flex>
        </Card>

        {/* Integration Grid */}
        <Flex vertical gap={24}>
          <Title level={4} className="!m-0 !text-[var(--app-text)] !font-black uppercase tracking-widest text-xs opacity-50">
            Available Channels
          </Title>
          <Row gutter={[32, 32]}>
            <Col xs={24} lg={12}>
              <ChannelCard 
                icon={GlobalOutlined}
                title="Website Widget"
                description="High-performance embeddable chat interface"
                status="active"
              />
            </Col>
            <Col xs={24} lg={12}>
              <ChannelCard 
                icon={SlackOutlined}
                title="Slack Workspace"
                description="Connect AI agents to your internal Slack teams"
                status="available"
              />
            </Col>
            <Col xs={24} lg={12}>
              <ChannelCard 
                icon={FaWhatsapp}
                title="WhatsApp Business"
                description="Reach users directly via WhatsApp Business API"
                status="available"
                type="whatsapp"
              />
            </Col>
            <Col xs={24} lg={12}>
              <ChannelCard 
                icon={CodeOutlined}
                title="REST API"
                description="Full access to neural inference via API hooks"
                status="active"
              />
            </Col>
          </Row>
        </Flex>

        {/* Ecosystem Callout */}
        <div className="p-10 bg-gradient-to-r from-[#285d91] to-[#1d4d7c] rounded-[40px] text-white shadow-2xl shadow-blue-900/20 overflow-hidden relative">
          <div className="absolute top-[-50%] right-[-10%] w-[300px] h-[300px] bg-white/10 rounded-full blur-[80px]" />
          <Flex justify="space-between" align="center" wrap="wrap" gap={32} className="relative z-10">
            <Flex vertical gap={8}>
              <Title level={3} className="!m-0 !text-white !font-black tracking-tighter">Need a Custom Link?</Title>
              <Text className="text-white/70 font-bold">Our architects can help you build bespoke API pipelines for your enterprise ecosystem.</Text>
            </Flex>
            <Button 
              size="large" 
              className="!h-14 !px-10 !rounded-2xl !bg-white !text-[#285d91] !border-none !font-black !uppercase !tracking-widest hover:!scale-105 transition-all"
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
          background: var(--app-border);
          border-radius: 10px;
        }
      `}</style>
    </div>
  );
}
