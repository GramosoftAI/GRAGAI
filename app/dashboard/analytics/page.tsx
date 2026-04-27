"use client";

import { Card, Col, Row, Typography, Space, Grid } from 'antd';
import { MessageSquare, Target, HelpCircle, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from "recharts";

const { Title, Text } = Typography;
const { useBreakpoint } = Grid;

function MetricCard({ change, icon: Icon, isPositive, value, label }: {
  change: string;
  icon: any;
  isPositive: boolean;
  value: string;
  label: string;
}) {
  return (
    <Card
      style={{
        background: "#0a1a18",
        border: "1px solid rgba(99,210,190,0.08)",
        borderRadius: 16,
        boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
        transition: "transform 0.2s, box-shadow 0.2s",
        cursor: "default",
      }}
      styles={{ body: { padding: 24 } }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(-4px)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 12px 40px rgba(99,210,190,0.1)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 8px 32px rgba(0,0,0,0.4)";
      }}
    >
      <Space direction="vertical" size={20} style={{ width: "100%" }}>
        <Row justify="space-between" align="middle">
          <Icon size={24} color="#63d2be" />
          <Text style={{ color: isPositive ? "#10b981" : "#ef4444", fontWeight: 700, fontSize: 14 }}>
            {isPositive ? "+" : ""}{change}
          </Text>
        </Row>
        <div>
          <Title level={2} style={{ color: "white", margin: 0, fontWeight: 800 }}>
            {value}
          </Title>
          <Text style={{ color: "#8baaa6", fontWeight: 500, fontSize: 14 }}>
            {label}
          </Text>
        </div>
      </Space>
    </Card>
  );
}

function QueryVolumeChart() {
  const chartData = [
    { day: "Mon", value: 45 },
    { day: "Tue", value: 62 },
    { day: "Wed", value: 38 },
    { day: "Thu", value: 85 },
    { day: "Fri", value: 72 },
    { day: "Sat", value: 30 },
    { day: "Sun", value: 52 },
  ];

  return (
    <Card
      style={{
        background: "#0a1a18",
        border: "1px solid rgba(99,210,190,0.08)",
        borderRadius: 20,
        boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
      }}
      styles={{ body: { padding: 32 } }}
    >
      <Space direction="vertical" size={24} style={{ width: "100%" }}>
        <Title level={4} style={{ color: "white", margin: 0 }}>
          Query Volume
        </Title>
        <div style={{ height: 300, width: "100%" }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#63d2be" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#63d2be" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="rgba(99,210,190,0.05)" />
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#8baaa6", fontSize: 12 }} dy={10} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: "#8baaa6", fontSize: 12 }} dx={-10} />
              <Tooltip
                contentStyle={{ backgroundColor: "#060f0e", borderColor: "rgba(99,210,190,0.2)", color: "#d4f0eb" }}
                itemStyle={{ color: "#63d2be" }}
              />
              <Area type="monotone" dataKey="value" stroke="#63d2be" strokeWidth={3} fillOpacity={1} fill="url(#colorValue)" animationDuration={2000} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Space>
    </Card>
  );
}

function UnansweredQuestions() {
  const questions = [
    "How do I integrate with Zapier?",
    "What's the SLA for enterprise?",
    "Can I export graph data?",
    "How to set up SSO?",
  ];

  return (
    <Card
      style={{
        background: "#0a1a18",
        border: "1px solid rgba(99,210,190,0.08)",
        borderRadius: 20,
        boxShadow: "0 20px 50px rgba(0,0,0,0.5)",
      }}
      styles={{ body: { padding: 32 } }}
    >
      <Space direction="vertical" size={24} style={{ width: "100%" }}>
        <Space align="center" size={12}>
          <HelpCircle size={20} color="#63d2be" />
          <Title level={4} style={{ color: "white", margin: 0 }}>
            Unanswered Questions
          </Title>
        </Space>
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          {questions.map((q, i) => (
            <Row
              key={i}
              justify="space-between"
              align="middle"
              style={{
                background: "rgba(139,170,166,0.05)",
                padding: "14px 16px",
                borderRadius: 12,
                cursor: "pointer",
                transition: "background 0.2s",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(99,210,190,0.08)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(139,170,166,0.05)")}
            >
              <Text style={{ color: "white", fontWeight: 500 }}>{q}</Text>
              <Text style={{ color: "#63d2be", fontWeight: 500, fontSize: 14 }}>
                Add to KB →
              </Text>
            </Row>
          ))}
        </Space>
      </Space>
    </Card>
  );
}

export default function AnalyticsPage() {
  const [isClient, setIsClient] = useState(false);
  useEffect(() => { setIsClient(true); }, []);

  const stats = [
    { label: "Total Queries", value: "3,847", change: "12%", icon: MessageSquare, isPositive: true },
    { label: "Accuracy",      value: "91.3%", change: "2.1%", icon: Target,       isPositive: true },
    { label: "Unanswered",    value: "42",    change: "8%",   icon: HelpCircle,   isPositive: false },
    { label: "Avg Confidence",value: "87%",   change: "5%",   icon: TrendingUp,   isPositive: true },
  ];

  return (
    <div style={{ color: "#d4f0eb" }}>
      <Space direction="vertical" size={32} style={{ width: "100%" }}>
        {/* Header */}
        <div>
          <Title style={{ color: "white", fontWeight: 800, letterSpacing: "-0.5px", marginBottom: 4 }}>
            Analytics
          </Title>
          <Text style={{ color: "#8baaa6", fontSize: 16 }}>
            Monitor bot performance and usage
          </Text>
        </div>

        {/* Metrics Grid */}
        <Row gutter={[24, 24]}>
          {stats.map((stat, i) => (
            <Col key={i} xs={24} sm={12} lg={6}>
              <MetricCard {...stat} />
            </Col>
          ))}
        </Row>

        {isClient && <QueryVolumeChart />}
        <UnansweredQuestions />
      </Space>
    </div>
  );
}