"use client";

import { Card, Col, Row, Typography, Space, Flex, Spin, Empty, Button, Tooltip } from 'antd';
import { MessageSquare, Target, HelpCircle, TrendingUp, PlusCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { useEffect, useState, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer
} from "recharts";
import useAxios from '../../hooks/useAxios';

const { Title, Text } = Typography;

interface AnalyticsData {
  metrics: {
    total_queries: { value: string; change: string; is_positive: boolean };
    accuracy: { value: string; change: string; is_positive: boolean };
    unanswered: { value: string; change: string; is_positive: boolean };
    avg_confidence: { value: string; change: string; is_positive: boolean };
  };
  query_volume: { day: string; value: number }[];
  unanswered_questions: string[];
}

function MetricCard({ change, icon: Icon, isPositive, value, label }: {
  change: string;
  icon: any;
  isPositive: boolean;
  value: string;
  label: string;
}) {
  return (
    <div className="group relative bg-[var(--app-surface)] border border-[var(--app-border)] p-8 rounded-[32px] shadow-[0_8px_30px_rgb(0,0,0,0.02)] hover:shadow-[0_20px_50px_rgba(40,93,145,0.06)] hover:-translate-y-1 transition-all duration-500 overflow-hidden">
      {/* Accent Background */}
      <div className={`absolute -top-10 -right-10 w-32 h-32 rounded-full blur-3xl opacity-0 group-hover:opacity-10 transition-opacity duration-700 ${isPositive ? 'bg-emerald-500' : 'bg-red-500'}`} />
      
      <Flex vertical gap={24} className="relative z-10">
        <Flex justify="space-between" align="center">
          <div className="w-12 h-12 rounded-2xl bg-[#285d91]/5 text-[#285d91] flex items-center justify-center shadow-inner group-hover:bg-[#285d91] group-hover:text-white transition-colors duration-500">
            <Icon size={20} />
          </div>
          <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
            isPositive ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'
          }`}>
            {isPositive ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
            {change}
          </div>
        </Flex>
        
        <div>
          <Title level={2} className="!m-0 !text-[var(--app-text)] !font-black !text-3xl tracking-tighter">
            {value}
          </Title>
          <Text className="text-[var(--app-text-soft)] font-bold text-xs uppercase tracking-[0.2em] mt-1 block">
            {label}
          </Text>
        </div>
      </Flex>
    </div>
  );
}

function QueryVolumeChart({ data }: { data: { day: string; value: number }[] }) {
  return (
    <div className="bg-[var(--app-surface)] border border-[var(--app-border)] p-10 rounded-[40px] shadow-[0_20px_50px_rgba(40,93,145,0.04)]">
      <Flex vertical gap={32}>
        <Flex justify="space-between" align="center">
          <div>
            <Title level={4} className="!m-0 !text-[var(--app-text)] !font-black tracking-tight">
              Intelligence Flow
            </Title>
            <Text className="text-[var(--app-text-soft)] font-bold text-xs uppercase tracking-widest mt-1 block">
              Daily query distribution and neural activity
            </Text>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-[var(--app-surface-muted)] rounded-xl text-[10px] font-black text-[#285d91] uppercase tracking-widest border border-[var(--app-border)]">
            Last 30 Days
          </div>
        </Flex>

        <div className="h-[350px] w-full">
          {data && data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <defs>
                  <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#285d91" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#285d91" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--app-border)" opacity={0.5} />
                <XAxis 
                  dataKey="day" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: "var(--app-text-soft)", fontSize: 10, fontWeight: 700 }} 
                  dy={15} 
                />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: "var(--app-text-soft)", fontSize: 10, fontWeight: 700 }} 
                  dx={-15} 
                />
                <RechartsTooltip
                  contentStyle={{ 
                    backgroundColor: "var(--app-surface)", 
                    border: "1px solid var(--app-border)", 
                    borderRadius: "16px",
                    boxShadow: "0 10px 30px rgba(0,0,0,0.1)",
                    padding: "12px 16px"
                  }}
                  itemStyle={{ color: "var(--app-text)", fontWeight: 800, fontSize: "14px" }}
                  labelStyle={{ color: "var(--app-text-soft)", fontWeight: 700, fontSize: "10px", marginBottom: "4px" }}
                />
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#285d91" 
                  strokeWidth={4} 
                  fillOpacity={1} 
                  fill="url(#chartGradient)" 
                  animationDuration={1500} 
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <Flex vertical align="center" justify="center" className="h-full opacity-30">
               <TrendingUp size={48} className="text-[#285d91] mb-4" />
               <Text className="font-black text-[#285d91]">No telemetry data available</Text>
            </Flex>
          )}
        </div>
      </Flex>
    </div>
  );
}

function UnansweredQuestions({ questions }: { questions: string[] }) {
  return (
    <div className="bg-[var(--app-surface)] border border-[var(--app-border)] p-10 rounded-[40px] shadow-[0_20px_50px_rgba(40,93,145,0.04)]">
      <Flex vertical gap={32}>
        <Flex align="center" gap={16}>
          <div className="w-12 h-12 rounded-2xl bg-[#285d91]/5 text-[#285d91] flex items-center justify-center">
            <HelpCircle size={24} />
          </div>
          <div>
            <Title level={4} className="!m-0 !text-[var(--app-text)] !font-black tracking-tight">
              Knowledge Gaps
            </Title>
            <Text className="text-[var(--app-text-soft)] font-bold text-xs uppercase tracking-widest mt-1 block">
              Identify and resolve unanswered queries
            </Text>
          </div>
        </Flex>

        {questions.length > 0 ? (
          <div className="space-y-3">
            {questions.map((q, i) => (
              <div
                key={i}
                className="group flex items-center justify-between p-6 bg-[var(--app-surface-muted)] hover:bg-[#285d91] rounded-2xl transition-all duration-300 cursor-pointer border border-transparent hover:border-transparent"
              >
                <Text className="text-[var(--app-text)] font-bold text-sm group-hover:text-white transition-colors">{q}</Text>
                <div className="flex items-center gap-2 text-[#285d91] group-hover:text-white font-black text-xs uppercase tracking-widest opacity-0 group-hover:opacity-100 translate-x-4 group-hover:translate-x-0 transition-all duration-300">
                  Sync to Knowledge Base <PlusCircle size={14} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Flex vertical align="center" justify="center" className="py-12 opacity-30">
            <Empty description={<Text className="font-black text-[#285d91]">Cognitive alignment complete. No gaps found.</Text>} />
          </Flex>
        )}
      </Flex>
    </div>
  );
}

export default function AnalyticsPage() {
  const [isClient, setIsClient] = useState(false);
  const [getAnalytics, response, loading] = useAxios<AnalyticsData>({ endpoint: "ANALYTICS_DASHBOARD" });
  const [userName, setUserName] = useState("");

  useEffect(() => {
    setIsClient(true);
    getAnalytics();
    const storedName = localStorage.getItem("userName");
    if (storedName) {
      setUserName(storedName.split(' ')[0]);
    }
  }, []);

  const stats = useMemo(() => {
    if (!response) return [];
    const root = (response as any).data || response;
    
    return [
      { label: "Total Volume", value: String(root.total_queries ?? 0), change: "12%", icon: MessageSquare, isPositive: true },
      { label: "Precision Score", value: `${root.accuracy_percent ?? 0}%`, change: "4%", icon: Target, isPositive: true },
      { label: "Cognitive Gaps", value: String(root.unanswered_count ?? 0), change: "2%", icon: HelpCircle, isPositive: false },
      { label: "Neural Confidence", value: `${Math.round((root.avg_confidence ?? 0) * 100)}%`, change: "1.2%", icon: TrendingUp, isPositive: true },
    ];
  }, [response]);

  const rootData = response ? ((response as any).data || response) : null;
  const chartData = (rootData?.trend_queries || []).map((item: any) => ({
    day: item.date || item.day || "Today",
    value: item.count || item.value || 0
  }));

  return (
    <div className="w-full pb-20 animate-in fade-in duration-700 relative">
      <Flex vertical gap={48}>
        {/* Header */}
        <div>
          <Title level={1} className="!m-0 !text-[var(--app-text)] !font-black !text-4xl md:!text-5xl tracking-tighter">
            {userName ? `${userName}'s` : "Intelligence"} Analytics
          </Title>
          <Text className="text-[var(--app-text-muted)] font-semibold text-base md:text-lg mt-2 block">
            Monitor neural performance, query precision, and cognitive alignment.
          </Text>
        </div>

        {/* Stats Grid */}
        <Row gutter={[32, 32]}>
          {(stats.length > 0 ? stats : [1,2,3,4]).map((stat: any, i) => (
            <Col key={i} xs={24} sm={12} lg={6}>
              {stats.length > 0 ? (
                <MetricCard {...stat} />
              ) : (
                <div className="h-48 bg-[var(--app-surface-muted)] rounded-[32px] animate-pulse border border-[var(--app-border)]" />
              )}
            </Col>
          ))}
        </Row>

        {/* Charts & Details */}
        {isClient && (
          <Flex vertical gap={32}>
            {response ? (
              <>
                <QueryVolumeChart data={chartData} />
                <UnansweredQuestions questions={rootData?.unanswered_questions || []} />
              </>
            ) : (
              <div className="h-[400px] bg-[var(--app-surface-muted)] rounded-[40px] animate-pulse border border-[var(--app-border)]" />
            )}
          </Flex>
        )}
      </Flex>

      {/* Loading Overlay */}
      {loading && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-transparent backdrop-blur-md transition-all duration-500">
           <div className="relative flex flex-col items-center gap-4 animate-in zoom-in-95 duration-500 text-center">
              <div className="relative">
                <div className="absolute inset-0 bg-[#285d91] rounded-full blur-[40px] opacity-20 animate-pulse" />
                <Spin className="relative z-10" />
              </div>
              <p className="text-[10px] font-black uppercase tracking-[0.3em] text-[#285d91] opacity-80">
                Syncing Telemetry
              </p>
           </div>
        </div>
      )}
    </div>
  );
}
