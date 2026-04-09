// providers/providers.tsx
"use client";

import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { type ReactNode } from "react";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <ChakraProvider value={defaultSystem}>
      {children}
    </ChakraProvider>
  );
}