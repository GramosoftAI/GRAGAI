// components/provider/GlobalProvider.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { App, ConfigProvider, theme as antdTheme } from "antd";
import { useState, type ReactNode } from "react";
import Providers from "./providers";
import { SessionProvider } from "next-auth/react"
import { GlobalLoader } from "./GlobalLoader";
import ThemeProvider, { useTheme } from "./ThemeProvider";

function ThemedConfigProvider({ children }: { children: ReactNode }) {
  const { isDark } = useTheme();

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: isDark ? "#34d399" : "#10b981",
          colorTextBase: isDark ? "#e2e8f0" : "#111827",
          colorTextSecondary: isDark ? "#94a3b8" : "#64748b",
          colorBgBase: isDark ? "#020617" : "#ffffff",
          colorBgContainer: isDark ? "#0f172a" : "#ffffff",
          colorBorder: isDark ? "#1e293b" : "#e2e8f0",
        },
      }}
    >
      <App>
        <GlobalLoader />
        <SessionProvider>
        <Providers>{children}</Providers>
        </SessionProvider>
      </App>
    </ConfigProvider>
  );
}

export default function GlobalProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ThemedConfigProvider>{children}</ThemedConfigProvider>
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
