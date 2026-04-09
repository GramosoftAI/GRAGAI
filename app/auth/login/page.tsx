"use client";

import {
  Box,
  Button,
  Flex,
  Heading,
  Input,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useState, FormEvent } from "react";
import useAxios from "@/lib/hooks/useAxios";
import { setCookie } from "@/lib/cookies";
import { AUTH_COOKIE_KEY } from "@/lib/config";
import { routes } from "@/lib/routes";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [request] = useAxios<unknown, { email: string; password: string }>({
    endpoint: "LOGIN",
    hideErrorMsg: false,
  });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await request({ data: { email: email.trim(), password } }, (res: any) => {
        const responseData = res?.data;

        // Save user name
        const user = responseData?.user;
        if (user) {
          localStorage.setItem("userName", `${user.first_name} ${user.last_name}`);
        }

        // Save permissions if present
        if (res?.roleInfo?.permissions) {
          localStorage.setItem("permission", JSON.stringify(res.roleInfo.permissions));
        }

        // to get the access token for cookie
        const token = responseData?.tokens?.access_token ?? "";
        setCookie(AUTH_COOKIE_KEY, token);
      });

      router.push( routes.dashboard);
    } catch (err: unknown) {
      let msg = "Login failed";
      if (typeof err === "object" && err && "data" in err) {
        const d = (err as { data?: unknown }).data;
        if (d && typeof d === "object" && "message" in d) {
          const m = (d as { message?: unknown }).message;
          if (typeof m === "string") msg = m;
        }
      }
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Flex
      minH="100vh"
      align="center"
      justify="center"
      bg="transparent"
      px="4"
    >
      <Box
        as="form"
        onSubmit={handleSubmit}
        w="full"
        minW="400px"
        borderWidth="1px"
        borderRadius="lg"
        bg="transparent"
        p="6"
        boxShadow="elevated"
        className="backdrop-blur-md! shadow-2xl!"
      >
        <VStack align="stretch" gap="4">
          <Box textAlign="center" mb="2">
            <Heading as="h1" size="md" mb="1">
              Sign in to Inbox
            </Heading>
            <Text fontSize="sm" color="muted">
              Enter your email and password to sign in.
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

          <Box>
            <label htmlFor="email">
              <Text fontSize="sm" mb="1" display="block">
                Email <span className="text-red-600">*</span>
              </Text>
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="username"
              required
            />
          </Box>

          <Box>
            <label htmlFor="password">
              <Text fontSize="sm" mb="1" display="block">
                Password <span className="text-red-600">*</span>
              </Text>
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </Box>

          <Button
            type="submit"
            colorPalette="brand"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>

          <Button
            type="button"
            variant="ghost"
            className="hover:bg-green-600! hover:text-white!"
            onClick={() => router.push(routes.register)}
          >
            Create account
          </Button>
        </VStack>
      </Box>
    </Flex>
  );
}