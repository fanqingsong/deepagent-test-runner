import { shortest } from "@antiwork/shortest";
import { authPayload, loginSteps, logoutSteps, requireLoginPageSteps } from "./helpers/flows";

shortest("Open the login page and verify AI Test Runner heading and Sign In form with email and password fields");

shortest([
  ...requireLoginPageSteps,
  "Try to sign in with empty email and verify an error message appears",
]);

shortest([
  ...requireLoginPageSteps,
  "Try to sign in with empty password and verify an error message appears",
]);

shortest([
  ...requireLoginPageSteps,
  "Try invalid credentials wrong@test.com / wrongpassword and verify an error message appears",
]);

shortest([
  ...requireLoginPageSteps,
  'Click "Forgot password?" and verify Reset Your Password form is shown',
]);

shortest([
  ...requireLoginPageSteps,
  'Click "Create account" and verify registration form is shown',
]);

shortest([
  ...requireLoginPageSteps,
  "Sign in with valid email and password using provided credentials",
], authPayload);

shortest([
  ...loginSteps,
  "Verify Test Dashboard heading is visible",
  ...logoutSteps,
], authPayload);
