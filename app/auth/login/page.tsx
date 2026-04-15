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
import { FaUser, FaLock, FaEye, FaEyeSlash } from "react-icons/fa";
import useAxios from "@/lib/hooks/useAxios";
import { setCookie } from "@/lib/cookies";
import { AUTH_COOKIE_KEY } from "@/lib/config";
import { routes } from "@/lib/routes";
import { useStore } from "@/lib/hooks/useStore";


export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
 // const [userID, setUserID] = useState<string>("");
  const [request] = useAxios<unknown, { email: string; password: string }>({
    endpoint: "LOGIN",
    hideErrorMsg: false,
  });

   const setUserId=useStore((s)=>s.setUserId)
  //const userId = useStore((s) => s.userId);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
  await request({ data: { email: email.trim(), password } }, (res: any) => {
  const responseData = res?.data; // ✅ added extra .data
  
  const user = responseData?.user;
  const userId = user?.id;
  console.log("User ID from response:", userId); // ✅ log the user ID

  if (userId) {
    setUserId(userId);
  }

  if (user) {
    localStorage.setItem("userName", `${user.first_name} ${user.last_name}`);
  }

  if (res?.data?.roleInfo?.permissions) {
    localStorage.setItem("permission", JSON.stringify(res.data.roleInfo.permissions));
  }

  const token = responseData?.tokens?.access_token ?? "";
  setCookie(AUTH_COOKIE_KEY, token);
});

      router.push(routes.dashboard);
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

  const iconWrapperStyle: React.CSSProperties = {
    position: "relative",
    display: "flex",
    alignItems: "center",
  };

  const leftIconStyle: React.CSSProperties = {
    position: "absolute",
    left: "0",
    top: "50%",
    transform: "translateY(-50%)",
    color: "#4ade80",
    fontSize: "14px",
    pointerEvents: "none",
  };

  const inputStyle: React.CSSProperties = {
    background: "transparent",
    border: "none",
    borderBottom: "1.5px solid #22c55e",
    borderRadius: "0",
    color: "#f0fff0",
    outline: "none",
    boxShadow: "none",
    paddingLeft: "22px",
    fontSize: "14px",
    width: "100%",
  };

  return (
    <Flex
      minH="100vh"
      align="center"
      justify="center"
      px="4"
      style={{
        background: "radial-gradient(ellipse at center, #0a1a0a 0%, #020802 100%)",
      }}
    >
      <Box
        style={{
          boxShadow:
            "0 0 0 1.5px #22c55e, 0 0 28px 5px rgba(34,197,94,0.38), 0 0 64px 8px rgba(34,197,94,0.12)",
          borderRadius: "14px",
          width: "680px",
          height: "420px",
          position: "relative",
          overflow: "hidden",
          flexShrink: 0,
        }}
      >
        {/* RIGHT: green panel */}
        <Flex
          align="center"
          justify="flex-end"
          style={{
            position: "absolute",
            inset: 0,
            background: "linear-gradient(140deg, #166534 0%, #16a34a 55%, #22c55e 100%)",
            paddingRight: "48px",
          }}
        >
          <Box style={{ width: "210px", textAlign: "center" }}>
            <Heading
              as="h2"
              style={{
                color: "#f0fff0",
                fontWeight: 900,
                fontSize: "2rem",
                lineHeight: 1.1,
                letterSpacing: "0.02em",
                marginBottom: "12px",
                textTransform: "uppercase",
              }}
            >
              WELCOME
              <br />
              BACK!
            </Heading>
            <Text fontSize="sm" style={{ color: "#dcfce7", lineHeight: 1.65 }}>
              Lorem ipsum, dolor sit amet consectetur adipisicing.
            </Text>
          </Box>
        </Flex>

        {/* LEFT: dark form panel */}
        <Box
          as="form"
          onSubmit={handleSubmit}
          style={{
            position: "absolute",
            inset: 0,
            background: "#060d06",
            clipPath: "polygon(0 0, 63% 0, 50% 100%, 0 100%)",
            display: "flex",
            alignItems: "center",
          }}
        >
          <VStack
            align="stretch"
            gap="4"
            style={{
              width: "50%",
              paddingLeft: "48px",
              paddingRight: "8px",
            }}
          >
            <Box textAlign="center" mb="1">
              <Heading
                as="h1"
                style={{
                  color: "#f0fff0",
                  fontWeight: 700,
                  fontSize: "1.35rem",
                  letterSpacing: "0.02em",
                }}
              >
                Login
              </Heading>
            </Box>

            {error && (
              <Box
                p="2"
                style={{
                  borderRadius: "6px",
                  borderLeft: "3px solid #22c55e",
                  background: "rgba(22,163,74,0.1)",
                }}
              >
                <Text fontSize="xs" style={{ color: "#86efac" }}>
                  {error}
                </Text>
              </Box>
            )}

            {/* Email field */}
            <Box>
              <label htmlFor="email">
                <Text fontSize="xs" mb="1" display="block" style={{ color: "#d1fae5" }}>
                  Email <span style={{ color: "#4ade80" }}>*</span>
                </Text>
              </label>
              <div style={iconWrapperStyle}>
                <span style={leftIconStyle}>
                  <FaUser />
                </span>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  required
                  style={inputStyle}
                />
              </div>
            </Box>

            {/* Password field */}
            <Box>
              <label htmlFor="password">
                <Text fontSize="xs" mb="1" display="block" style={{ color: "#d1fae5" }}>
                  Password <span style={{ color: "#4ade80" }}>*</span>
                </Text>
              </label>
              <div style={iconWrapperStyle}>
                <span style={leftIconStyle}>
                  <FaLock />
                </span>
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  style={{ ...inputStyle, paddingRight: "28px" }}
                />
                {/* Eye toggle */}
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  style={{
                    position: "absolute",
                    right: "0",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: "0",
                    display: "flex",
                    alignItems: "center",
                    color: "#4ade80",
                    fontSize: "14px",
                  }}
                >
                  {showPassword ? <FaEyeSlash /> : <FaEye />}
                </button>
              </div>
            </Box>

            <Button
              type="submit"
              disabled={isSubmitting}
              style={{
                background: "linear-gradient(90deg, #16a34a, #22c55e)",
                color: "#f0fff0",
                borderRadius: "999px",
                fontWeight: 600,
                fontSize: "14px",
                padding: "8px 0",
                boxShadow: "0 2px 14px rgba(34,197,94,0.4)",
                border: "none",
                cursor: isSubmitting ? "not-allowed" : "pointer",
                opacity: isSubmitting ? 0.7 : 1,
                transition: "opacity 0.2s",
              }}
            >
              {isSubmitting ? "Signing in…" : "Login"}
            </Button>

            <Text fontSize="xs" textAlign="center" style={{ color: "#d1fae5" }}>
              Don&apos;t have an account?{" "}
              <span
                onClick={() => router.push(routes.register)}
                style={{ color: "#4ade80", cursor: "pointer", fontWeight: 600 }}
              >
                Sign Up
              </span>
            </Text>
          </VStack>
        </Box>
      </Box>
    </Flex>
  );
}