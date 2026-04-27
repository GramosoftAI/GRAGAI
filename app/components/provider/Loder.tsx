// components/provider/Loder.tsx
"use client";
import { Flex, Spin } from "antd";

export const Loader = () => (
  <Flex
    align="center"
    justify="center"
    style={{
      position: "fixed",    // ← stays on top of page
      inset: 0,             // ← covers full screen
      backgroundColor: "rgba(255, 255, 255, 0.6)",  // ← semi-transparent
      zIndex: 9999,         // ← above everything
    }}
  >
    <Spin size="large" />
  </Flex>
);