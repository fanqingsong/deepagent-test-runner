import { shortest } from "@antiwork/shortest";
import { E2E_CREDENTIALS } from "./helpers/credentials";

shortest("Open the login page and verify the AI Test Runner sign-in form is visible with email and password fields");

shortest("Sign in to AI Test Runner using email and password", {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
});

shortest([
  "Sign in to AI Test Runner with valid email and password",
  "After login, verify the dashboard page shows Test Dashboard heading",
], {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
});
