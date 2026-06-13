import { shortest } from "@antiwork/shortest";
import { E2E_CREDENTIALS } from "./helpers/credentials";

shortest([
  "Sign in to AI Test Runner with email and password",
  "Navigate to the 测试管理 page via sidebar or hash #tests",
  "Verify the 测试管理 page title is visible",
], {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
});
