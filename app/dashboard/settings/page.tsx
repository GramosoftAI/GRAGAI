"use client";

import { toast } from "sonner";
import React, { useState } from "react";
import { Box, Heading, VStack, Text, Switch, Flex, Separator, Field, Input, Button } from "@chakra-ui/react";

export default function SettingsPage() {
  const [orgName, setOrgName] = useState("Acmp corp");
  const [apiKey, setApiKey] = useState("gm_sk_****************");
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [analyticsReports, setAnalyticsReports] = useState(true);

  const handleSave = () => {
    toast.success("Settings saved successfully.");
  }
  return (
    <Box mx="auto" pb={20}>
      <VStack align="start" mb={10} gap={2}>
        <Heading as="h1" size="3xl" fontWeight="bold" color="white" letterSpacing="tight">
          Settings
        </Heading>
        <Text color="gray.500" fontSize="lg">
          Manage your account and preferences
        </Text>
      </VStack>

      <VStack gap={8} align="stretch">
        {/* Profile Section */}
        <Box
        maxW="800px"
          bg="#101514"
          borderRadius="2xl"
          p={8}
          border="1px solid"
          borderColor="rgba(99,210,190,0.08)"
          boxShadow="0 4px 24px rgba(0,0,0,0.2)"
        >
          <Heading as="h3" size="lg" color="white" fontWeight="bold" mb={6}>
            Profile
          </Heading>

          <VStack gap={6} align="stretch">
            <Field.Root>
              <Field.Label color="gray.400" fontSize="sm" fontWeight="medium" mb={2}>
                Organization Name
              </Field.Label>
              <Input
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                bg="#0a0f0e"
                border="1px solid"
                borderColor="rgba(99,210,190,0.1)"
                borderRadius="xl"
                color="white"
                px={4}
                py={6}
                _focus={{
                  borderColor: "rgba(99,210,190,0.4)",
                  boxShadow: "0 0 0 1px rgba(99,210,190,0.4)",
                }}
              />
            </Field.Root>

            <Field.Root>
              <Field.Label color="gray.400" fontSize="sm" fontWeight="medium" mb={2}>
                API Key
              </Field.Label>
              <Input
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                type="password"
                bg="#0a0f0e"
                border="1px solid"
                borderColor="rgba(99,210,190,0.1)"
                borderRadius="xl"
                color="white"
                px={4}
                py={6}
                _focus={{
                  borderColor: "rgba(99,210,190,0.4)",
                  boxShadow: "0 0 0 1px rgba(99,210,190,0.4)",
                }}
              />
            </Field.Root>
          </VStack>
        </Box>

        {/* Preferences Section */}
        <Box
        maxW="800px"
          bg="#101514"
          borderRadius="2xl"
          p={8}
          border="1px solid"
          borderColor="rgba(99,210,190,0.08)"
          boxShadow="0 4px 24px rgba(0,0,0,0.2)"
        >
          <Heading as="h3" size="lg" color="white" fontWeight="bold" mb={6}>
            Preferences
          </Heading>

          <VStack gap={8} align="stretch">
            <Flex justify="space-between" align="center">
              <VStack align="start" gap={0}>
                <Text color="white" fontWeight="bold" fontSize="md">
                  Email Notifications
                </Text>
                <Text color="gray.500" fontSize="sm">
                  Get notified about unanswered questions
                </Text>
              </VStack>
              <Switch.Root
                colorPalette="teal"
                size="lg"
                checked={emailNotifications}
                onCheckedChange={(e) => setEmailNotifications(e.checked)}
              >
                <Switch.HiddenInput />
                <Switch.Control
                  bg="#0a0f0e"
                  _checked={{ bg: "#63d2be" }}
                >
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </Flex>

            <Separator borderColor="rgba(99,210,190,0.05)" />

            <Flex justify="space-between" align="center">
              <VStack align="start" gap={0}>
                <Text color="white" fontWeight="bold" fontSize="md">
                  Analytics Reports
                </Text>
                <Text color="gray.500" fontSize="sm">
                  Weekly performance summaries
                </Text>
              </VStack>
              <Switch.Root
                colorPalette="teal"
                size="lg"
                checked={analyticsReports}
                onCheckedChange={(e) => setAnalyticsReports(e.checked)}
              >
                <Switch.HiddenInput />
                <Switch.Control
                  bg="#0a0f0e"
                  _checked={{ bg: "#63d2be" }}
                >
                  <Switch.Thumb />
                </Switch.Control>
              </Switch.Root>
            </Flex>
          </VStack>
        </Box>
        {/* Save Changes Button */}
        <Flex justify="flex-end" mt={4} maxW="800px">
          <Button
            onClick={handleSave}
            bg="#63d2be"
            color="black"
            size="xl"
            px={10}
            py={7}
            borderRadius="xl"
            fontWeight="bold"
            _hover={{ bg: "#4ec5af", transform: "translateY(-1px)" }}
            _active={{ bg: "#3bb29c", transform: "translateY(0)" }}
            transition="all 0.2s"
          >
            Save Changes
          </Button>
        </Flex>
      </VStack>
    </Box>
  )
}
