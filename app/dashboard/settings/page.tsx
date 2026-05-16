"use client";

import { 
  Flex, Typography, Card, Input, Switch, Button, 
  App, Space, Divider, Row, Col 
} from "antd";
import { 
  UserOutlined, KeyOutlined, BellOutlined, 
  BarChartOutlined, SaveOutlined, TeamOutlined,
  SafetyCertificateOutlined
} from "@ant-design/icons";
import { useState, useEffect } from "react";

const { Title, Text } = Typography;

// ─── Settings Section Component ───────────────────────────────────────────────

function SettingsSection({ title, children, icon: Icon }: { title: string; children: React.ReactNode; icon: any }) {
  return (
    <Card 
      className="bg-[var(--app-surface)] border border-[var(--app-border)] rounded-[32px] shadow-[0_10px_30px_rgba(40,93,145,0.03)] overflow-hidden"
      styles={{ body: { padding: 32 } }}
    >
      <Flex vertical gap={24}>
        <Flex align="center" gap={12}>
          <div className="w-10 h-10 rounded-xl bg-[#285d91]/5 text-[#285d91] flex items-center justify-center text-lg shadow-inner">
            <Icon />
          </div>
          <Title level={4} className="!m-0 !text-[var(--app-text)] !font-black tracking-tight">
            {title}
          </Title>
        </Flex>
        {children}
      </Flex>
    </Card>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const { notification } = App.useApp();
  const [loading, setLoading] = useState(false);
  
  const handleSave = () => {
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      notification.success({
        title: 'Settings Synchronized',
        description: 'Your profile preferences have been successfully updated.',
        className: "custom-toast-success"
      });
    }, 1500);
  };

  return (
    <div className="w-full pb-20 animate-in fade-in duration-1000">
      <Flex vertical gap={40}>
        
        {/* Header Section */}
        <Flex vertical gap={8}>
          <Title level={2} className="!m-0 !text-[var(--app-text)] !font-black !text-3xl tracking-tighter">
            Account Settings
          </Title>
          <Text className="text-[var(--app-text-muted)] font-semibold text-sm max-w-xl leading-relaxed">
            Manage your organization profile, security protocols, and system-wide preferences.
          </Text>
        </Flex>

        <Flex vertical gap={24} className="max-w-4xl">
          
          {/* Profile Section */}
          <SettingsSection title="Organization Profile" icon={TeamOutlined}>
            <Row gutter={[24, 24]}>
              <Col xs={24}>
                <Flex vertical gap={6}>
                  <Text className="font-black text-[9px] uppercase tracking-widest text-[var(--app-text-soft)]">Organization Name</Text>
                  <Input 
                    placeholder="Acme Corp" 
                    defaultValue="GraphMind AI"
                    className="h-12 !rounded-xl !bg-[var(--app-surface-muted)] !border-none !font-bold !text-[var(--app-text)] !text-sm focus:!ring-2 focus:!ring-[#285d91]/10" 
                    prefix={<TeamOutlined className="text-[var(--app-text-soft)] mr-2" />}
                  />
                </Flex>
              </Col>
              <Col xs={24}>
                <Flex vertical gap={6}>
                  <Text className="font-black text-[9px] uppercase tracking-widest text-[var(--app-text-soft)]">Master API Key</Text>
                  <Input.Password 
                    defaultValue="gm_sk_4928f37454b04c9dba4e9eb10285786e"
                    className="h-12 !rounded-xl !bg-[var(--app-surface-muted)] !border-none !font-bold !text-[var(--app-text)] !text-sm focus:!ring-2 focus:!ring-[#285d91]/10" 
                    prefix={<KeyOutlined className="text-[var(--app-text-soft)] mr-2" />}
                  />
                </Flex>
              </Col>
            </Row>
          </SettingsSection>

          {/* Preferences Section */}
          <SettingsSection title="Intelligence Preferences" icon={SafetyCertificateOutlined}>
            <div className="space-y-4">
              <Flex align="center" justify="space-between" className="p-4 bg-[var(--app-surface-muted)] rounded-[20px] border border-[var(--app-border)]/30">
                <Flex vertical gap={2}>
                  <Title level={5} className="!m-0 !text-[var(--app-text)] !font-black !text-sm">Email Notifications</Title>
                  <Text className="text-[var(--app-text-soft)] font-bold text-[10px]">Get notified about unanswered questions and critical gaps.</Text>
                </Flex>
                <Switch defaultChecked size="small" className="bg-[#285d91]" />
              </Flex>

              <Flex align="center" justify="space-between" className="p-4 bg-[var(--app-surface-muted)] rounded-[20px] border border-[var(--app-border)]/30">
                <Flex vertical gap={2}>
                  <Title level={5} className="!m-0 !text-[var(--app-text)] !font-black !text-sm">Analytics Reports</Title>
                  <Text className="text-[var(--app-text-soft)] font-bold text-[10px]">Receive weekly performance summaries and cognitive insights.</Text>
                </Flex>
                <Switch defaultChecked size="small" className="bg-[#285d91]" />
              </Flex>

              <Flex align="center" justify="space-between" className="p-4 bg-[var(--app-surface-muted)] rounded-[20px] border border-[var(--app-border)]/30">
                <Flex vertical gap={2}>
                  <Title level={5} className="!m-0 !text-[var(--app-text)] !font-black !text-sm">Neural Feedback Loop</Title>
                  <Text className="text-[var(--app-text-soft)] font-bold text-[10px]">Allow the system to learn from user corrections automatically.</Text>
                </Flex>
                <Switch size="small" className="bg-[#285d91]" />
              </Flex>
            </div>
          </SettingsSection>

          {/* Save Action */}
          <Flex justify="flex-end" className="mt-4">
            <Button 
              type="primary" 
              size="large" 
              loading={loading}
              icon={<SaveOutlined />}
              onClick={handleSave}
              className="!h-14 !px-10 !rounded-2xl !bg-[#285d91] !border-none !font-black !text-sm !uppercase !tracking-widest shadow-xl shadow-blue-900/10 hover:!scale-[1.02] transition-all"
            >
              Save Configuration
            </Button>
          </Flex>

        </Flex>
      </Flex>
    </div>
  );
}
