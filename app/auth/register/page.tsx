"use client";

import { Box, Button, Flex, Heading, Input, Text, VStack } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useState, FormEvent } from "react";
import { routes } from "@/lib/routes";
import useAxios from "@/lib/hooks/useAxios";
import { RegisterPayload } from "@/components/ui/type";

export default function RegisterPage() {
  const router = useRouter();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [register]=useAxios<RegisterPayload>({endpoint:"REGISTER",successCb() {
      router.back()
  }});

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!firstName || !lastName || !email || !password || !tenantName) {
      setError("Please fill in all required fields.");
      return;
    }

    const payload:RegisterPayload = {
      email,
      first_name: firstName,
      last_name: lastName,
      password,
      tenant_name: tenantName,
    };
    register({data:payload})

    console.log("Register payload:", payload);
  }

  const fields = [
    {
      id: "email", label: "Email", type: "email",
      value: email, onChange: (v: string) => setEmail(v),
      autoComplete: "email",
    },
    {
      id: "password", label: "Password", type: "password",
      value: password, onChange: (v: string) => setPassword(v),
      autoComplete: "new-password",
    },
    {
      id: "tenantName", label: "User Category", type: "text",
      value: tenantName, onChange: (v: string) => setTenantName(v),
      autoComplete: "off",
    },
  ];

  return (
    <Flex minH="100vh" align="center" justify="center" bg="transparent" px="4">
      <Box
        as="form"
        onSubmit={handleSubmit}
        w="full"
        minW="400px"
        borderWidth="1px"
        borderRadius="lg"
        bg="transparentb"
        p="6"
        boxShadow="elevated"
        className="backdrop-blur-md! shadow-2xl!"
      >
        <VStack align="stretch" gap="4">
          <Box textAlign="center" mb="2">
            <Heading as="h1" size="md" mb="1">
              Create an Account
            </Heading>
            <Text fontSize="sm" color="muted">
              Fill in the details below to get started.
            </Text>
          </Box>

          {error && (
            <Box
              borderWidth="1px"
              borderRadius="md"
              borderColor="red.300"
              bg="red.50"
              _dark={{ bg: "red.900", borderColor: "red.600" }}
              p="3"
            >
              <Text fontSize="sm" color="red.700" _dark={{ color: "red.100" }}>
                {error}
              </Text>
            </Box>
          )}

          <Flex gap="3">
            <Box flex="1">
              <label htmlFor="firstName">
                <Text fontSize="sm" mb="1" display="block">
                  First Name <span className="text-red-600">*</span>
                </Text>
              </label>
              <Input
                id="firstName"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                autoComplete="given-name"
                required
              />
            </Box>
            <Box flex="1">
              <label htmlFor="lastName">
                <Text fontSize="sm" mb="1" display="block">
                  Last Name <span className="text-red-600">*</span>
                </Text>
              </label>
              <Input
                id="lastName"
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                autoComplete="family-name"
                required
              />
            </Box>
          </Flex>

          {fields.map((field) => (
            <Box key={field.id}>
              <label htmlFor={field.id}>
                <Text fontSize="sm" mb="1" display="block">
                  {field.label} <span className="text-red-600">*</span>
                </Text>
              </label>
              <Input
                id={field.id}
                type={field.type}
                value={field.value}
                onChange={(e) => field.onChange(e.target.value)}
                autoComplete={field.autoComplete}
                required
              />
            </Box>
          ))}

          <Button type="submit" colorPalette="brand" mt="2"
          className="hover:bg-green-600! hover:text-white!">
            Create Account
          </Button>

        </VStack>
      </Box>
    </Flex>
  );
}