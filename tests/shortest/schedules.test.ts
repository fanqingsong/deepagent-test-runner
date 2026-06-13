import { shortest } from "@antiwork/shortest";
import { E2E_CREDENTIALS } from "./helpers/credentials";

shortest([
  "Sign in to AI Test Runner with email and password",
  "Navigate to the 调度配置 page via sidebar or hash #schedules",
  "Verify the 调度配置 page title is visible",
], {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
});
