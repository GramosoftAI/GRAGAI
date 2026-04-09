"use client";

import { Heading, VStack, Text, Box, IconButton, Flex, HStack, Icon, Badge, SimpleGrid } from "@chakra-ui/react";
import { useState } from "react";
import { FaSlack } from "react-icons/fa";
import { FiCheck, FiCode, FiCopy, FiGlobe, FiMessageSquare } from "react-icons/fi";
import { toast } from "sonner";

const IntegrationHeader = ({ title, subtitle }: { title: string; subtitle: string }) => (
    <VStack align="start" mb={8} gap={2}>
        <Heading as="h1" size="xl" fontWeight="bold" color="white">
            {title}
        </Heading>
        <Text color="gray.400" fontSize="lg">
            {subtitle}
        </Text>
    </VStack>
);

const ScriptSnippet = ({ title, description, code }: { title: string; description: string; code: string }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            toast.success("Script copied to clipboard.");
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            toast.error("Failed to copy. Please try again.");
        }
    }

    const highlightCode = (line: string) => {
        return line
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/(".*?")/g, '<span style="color: #63d2be">$1</span>')
            .replace(/(src|data-bot-id|data-theme)=/g, '<span style="color: #4ade80">$1</span>=')
            .replace(/&lt;\/?script/g, '<span style="color: #10b981">$&</span>');
    };

    return (
        <Box bg="#101514" borderRadius="2xl" p={8} border="1px solid" borderColor="rgba(99,210,190,0.08)" w="full" mb={8}>
            <VStack align="start" gap={1} mb={6}>
                <Heading as="h3" size="md" color="white" fontWeight="bold">{title}</Heading>
                <Text color="gray.500" fontSize="sm">{description}</Text>
            </VStack>
            <Box position="relative" bg="#0a0f0e" borderRadius="2xl" p={8} border="1px solid" borderColor="rgba(99,210,190,0.08)" w="full">
                <IconButton
                    aria-label="Copy script"
                    position="absolute" top={4} right={4} variant="ghost" color="gray.400"
                    _hover={{ color: "green.400", bg: "transparent" }}
                    onClick={handleCopy}
                    size="sm"
                >
                    {copied ? <FiCheck /> : <FiCopy />}
                </IconButton>
                <pre style={{ margin: 0, overflowX: "auto" }}>
                    <code style={{ color: "#63d2be" }}>
                        {code.split('\n').map((line, i) => (
                            <div key={i} style={{ display: 'flex' }}>
                                <Text color="gray.600" mr={4} userSelect="none" minW="1.5em" textAlign="right"></Text>
                                <div dangerouslySetInnerHTML={{ __html: highlightCode(line) }} />
                            </div>
                        ))}
                    </code>
                </pre>
            </Box>
        </Box>
    )
}

const IntegrationCard = ({ title, description, icon, status }: { title: string; description: string; icon: any; status: string }) => {
    const getStatusProps = (status: string) => {
        switch (status) {
            case "active": return { label: "active", color: "green.400", bg: "rgba(16, 185, 129, 0.1)" };
            case "available": return { label: "available", color: "gray.400", bg: "rgba(156, 163, 175, 0.1)" };
            default: return { label: "coming soon", color: "orange.400", bg: "rgba(251, 146, 60, 0.1)" };
        }
    };
    const statusProps = getStatusProps(status);
    return (
        <Box
            bg="#121817" borderRadius="2xl" p={6} border="1px solid" borderColor="rgba(99,210,190,0.08)"
            transition="all 0.2s" _hover={{ borderColor: "rgba(99,210,190,0.2)", transform: "translateY(-2px)", bg: "#161e1d" }}
            cursor="pointer" flex="1" minW="300px"
        >
            <Flex justify="space-between" align="start">
                <HStack gap={4} align="center">
                    <Flex bg="rgba(99,210,190,0.05)" p={3} borderRadius="xl" color="green.400" align="center" justify="center" border="1px solid" borderColor="rgba(99,210,190,0.1)">
                        <Icon as={icon} boxSize={6} />
                    </Flex>
                    <VStack align="start" gap={0}>
                        <Text color="white" fontWeight="bold" fontSize="lg">{title}</Text>
                        <Text color="gray.500" fontSize="sm">{description}</Text>
                    </VStack>
                </HStack>
                <Badge px={3} py={1} borderRadius="full" color={statusProps.color} bg={statusProps.bg} textTransform="lowercase" fontSize="xs">
                    {statusProps.label}
                </Badge>
            </Flex>
        </Box>
    );
}

export default function IntegrationsPage() {
    const embedCode = `<script src="https://graphmind.ai/widget.js"
  data-bot-id="bot_abc123"
  data-theme="dark">
</script>`;
  return (
    <Box maxW="1200px" mx="auto">
      <IntegrationHeader title="Integrations" subtitle="Deploy your bot across channels" />
      <ScriptSnippet title="Embed Script" description="Add this to your website to enable the chat widget" code={embedCode} />
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={6}>
        <IntegrationCard title="Website Widget" description="Embeddable chat widget" icon={FiGlobe} status="active" />
        <IntegrationCard title="Slack" description="Connect to Slack workspace" icon={FaSlack} status="available" />
        <IntegrationCard title="WhatsApp" description="Connect via Meta API" icon={FiMessageSquare} status="available" />
        <IntegrationCard title="API" description="REST API access" icon={FiCode} status="active" />
      </SimpleGrid>
    </Box>
  );
}