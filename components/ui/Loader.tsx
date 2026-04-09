// components/ui/loader.tsx
"use client";

import { Spinner, Text, VStack } from "@chakra-ui/react";

export const Loader = () => (
  <VStack h="100vh" justify="center" colorPalette="teal">
    <Spinner color="colorPalette.600" size="xl" />
    <Text color="colorPalette.600">Loading...</Text>
  </VStack>
);