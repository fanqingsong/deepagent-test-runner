import { shortest } from "@antiwork/shortest";
import { E2E_CREDENTIALS } from "./helpers/credentials";

shortest([
  "Sign in to AI Test Runner using email #login-email and password #login-password, then click Sign In",
  "Verify the dashboard page displays Test Dashboard heading",
], {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
});
