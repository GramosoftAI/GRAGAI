"use client";

import { Box, Flex, Icon, VStack, Text, Heading, SimpleGrid, HStack } from '@chakra-ui/react'
import { MessageSquare, Target, HelpCircle, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";


function MetricCard({
  change,
  icon,
  isPositive,
  value,
  label
}: {
  change: string;
  icon: any;
  isPositive: boolean;
  value: string;
  label: string;
}) {
  return (
    <Box bg="#0a1a18"
      borderWidth="1px" borderColor="rgba(99,210,190,0.08)" borderRadius="xl"
      p="6" boxShadow="0 8px 32px rgba(0,0,0,0.4)"
      transition="transform 0.2s, box-shadow 0.2s"
      _hover={{
        transform: "translateY(-4px)",
        boxShadow: "0 12px 40px rgba(99,210,190,0.1)"
      }}>
      <VStack align="stretch" gap="5">
        <Flex justify="space-between" align="center">
          <Icon as={icon} boxSize={6} color="#63d2be" />
          <Text fontSize="sm" fontWeight="bold" color={isPositive ? "#10b981" : "#ef4444"}>
            {isPositive ? "+" : ""}{change}
          </Text>
        </Flex>

        <Box>
          <Text fontSize="3xl" fontWeight="800" color="white" mb="1">
            {value}
          </Text>
          <Text fontSize="sm" color="#8baaa6" fontWeight="500">
            {label}
          </Text>
        </Box>
      </VStack>
    </Box>
  )
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
    <Box
      bg="#0a1a18"
      borderWidth="1px"
      borderColor="rgba(99,210,190,0.08)"
      borderRadius="2xl"
      p="8"
      boxShadow="0 20px 50px rgba(0,0,0,0.5)"
      mt="8">
      <VStack align="stretch" gap="6">
        <Heading as="h3" size="md" color="white">
          Query Volume
        </Heading>
        <Box h="300px" w="100%">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#63d2be" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#63d2be" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                strokeDasharray="3 3"
                stroke="rgba(99,210,190,0.05)" />
              <XAxis
                dataKey="day"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#8baaa6", fontSize: 12 }}
                dy={10} />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#8baaa6", fontSize: 12 }}
                dx={-10} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#060f0e",
                  borderColor: "rgba(99,210,190,0.2)",
                  color: "#d4f0eb"
                }}
                itemStyle={{ color: "#63d2be" }}
              />
              <Area
                type="monotone" // This creates the smooth curved line
                dataKey="value"
                stroke="#63d2be"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorValue)"
                animationDuration={2000} />
            </AreaChart>
          </ResponsiveContainer>
        </Box>
      </VStack>
    </Box>
  )
}

function UnansweredQuestions() {
  const questions = [
    "How do I integrate with Zapier?",
    "What's the SLA for enterprise?",
    "Can I export graph data?",
    "How to set up SSO?",
  ];
  return (
    <Box
      bg="#0a1a18"
      borderWidth="1px"
      borderColor="rgba(99,210,190,0.08)"
      borderRadius="2xl"
      p="8"
      boxShadow="0 20px 50px rgba(0,0,0,0.5)"
      mt="8"
    >
      <VStack align="stretch" gap="6">
        <HStack gap="3">
          <Icon as={HelpCircle} boxSize={5} color="#63d2be" />
          <Heading as="h3" size="md" color="white">
            Unanswered Questions
          </Heading>
        </HStack>
        <VStack align="stretch" gap="3">
          {questions.map((q, i) => (
            <Flex
              key={i}
              bg="rgba(139,170,166,0.05)"
              p="4"
              borderRadius="xl"
              justify="space-between"
              align="center"
              _hover={{ bg: "rgba(99,210,190,0.08)" }}
              cursor="pointer"
              transition="background 0.2s"
            >
              <Text color="white" fontWeight="500">
                {q}
              </Text>
              <Text fontSize="sm" color="#63d2be" fontWeight="500">
                Add to KB &rarr;
              </Text>
            </Flex>
          ))}
        </VStack>
      </VStack>
    </Box>
  );
}

export default function AnalyticsPage() {
  const [isClient, setIsClient] = useState(false);
  useEffect(() => {
    setIsClient(true);
  }, []);
  const stats = [
    {
      label: "Total Queries",
      value: "3,847",
      change: "12%",
      icon: MessageSquare,
      isPositive: true,
    },
    {
      label: "Accuracy",
      value: "91.3%",
      change: "2.1%",
      icon: Target,
      isPositive: true,
    },
    {
      label: "Unanswered",
      value: "42",
      change: "8%",
      icon: HelpCircle,
      isPositive: false,
    },
    {
      label: "Avg Confidence",
      value: "87%",
      change: "5%",
      icon: TrendingUp,
      isPositive: true,
    },
  ];
  return (
    <Box color="#d4f0eb">
      <VStack align="stretch" gap="8">
        {/* Header */}
        <Box>
          <Heading as="h1" size="2xl" fontWeight="800" letterSpacing="tight" mb="2">
            Analytics
          </Heading>
          <Text color="#8baaa6" fontSize="lg">
            Monitor bot performance and usage
          </Text>
        </Box>
        {/* Metrics Grid */}
        <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap="6">
          {stats.map((stat, index) => (
            <MetricCard key={index} {...stat} />
          ))}
        </SimpleGrid>
        {isClient && <QueryVolumeChart />}
        { <UnansweredQuestions />}
      </VStack>
    </Box>
  )
}
