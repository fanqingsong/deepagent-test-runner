import type { ShortestConfig } from "@antiwork/shortest";

const baseUrl = process.env.BASE_URL || "http://localhost:8085";

export default {
  headless: process.env.SHORTEST_HEADLESS === "true",
  baseUrl,
  testPattern: "*.test.ts",
  browser: {
    contextOptions: {
      ignoreHTTPSErrors: true,
    },
  },
  ai: {
    provider: "glm",
    model: process.env.SHORTEST_GLM_MODEL || process.env.LLM_MODEL || "glm-4-plus",
    baseURL:
      process.env.SHORTEST_GLM_BASE_URL ||
      process.env.LLM_BASE_URL ||
      "https://open.bigmodel.cn/api/paas/v4/",
  },
} satisfies ShortestConfig;
