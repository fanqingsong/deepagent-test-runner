import type { ShortestConfig } from "@antiwork/shortest";

export default {
  headless: false,
  baseUrl: "http://localhost:3000",
  testPattern: "tests/shortest/cases/*.test.ts",
  ai: {
    provider: "anthropic"
  }
} satisfies ShortestConfig;