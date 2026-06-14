import type { ShortestConfig } from "@antiwork/shortest";
import { existsSync } from "fs";
import { join } from "path";

const baseUrl = process.env.BASE_URL || "http://localhost:8085";

/** shortest GLM provider requires baseURL to match known prefixes (with trailing slash). */
const normalizeGlmBaseURL = (url: string) => `${url.replace(/\/+$/, "")}/`;

const glmBaseURL = normalizeGlmBaseURL(
  process.env.SHORTEST_GLM_BASE_URL ||
    process.env.LLM_BASE_URL ||
    "https://open.bigmodel.cn/api/paas/v4/"
);

const authStatePath = join(process.cwd(), ".shortest/auth-state.json");
const useAuthState =
  process.env.SHORTEST_SKIP_AUTH_STATE !== "1" && existsSync(authStatePath);

/** With saved session, land on dashboard — skips slow AI navigation step. */
const appBaseUrl = useAuthState
  ? `${baseUrl.replace(/\/$/, "")}/#dashboard`
  : baseUrl;

export default {
  headless: process.env.SHORTEST_HEADLESS === "true",
  baseUrl: appBaseUrl,
  testPattern: "*.test.ts",
  browser: {
    contextOptions: {
      ignoreHTTPSErrors: true,
      ...(useAuthState ? { storageState: authStatePath } : {}),
    },
  },
  ai: {
    provider: "glm",
    model: process.env.SHORTEST_GLM_MODEL || process.env.LLM_MODEL || "glm-4-plus",
    baseURL: glmBaseURL,
  },
} satisfies ShortestConfig;
