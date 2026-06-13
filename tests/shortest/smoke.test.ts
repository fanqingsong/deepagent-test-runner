import { shortest } from "@antiwork/shortest";
import { E2E_CREDENTIALS } from "./helpers/credentials";

shortest([
  "Open the app login page",
  "Sign in with email and password",
  "Verify dashboard shows Test Dashboard heading",
], {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
});
