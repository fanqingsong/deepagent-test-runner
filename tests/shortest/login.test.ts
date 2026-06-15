import { shortest } from "@antiwork/shortest";
import { authPayload, loginSteps, logoutSteps, requireLoginPageSteps } from "./helpers/flows";
import { actThenAssert, assertPage } from "./helpers/prompts";

shortest(
  assertPage("AI Test Runner", "Email Address", "Password", "Sign In"),
);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    "Without filling any fields, click the Sign In button.",
    'an error message such as "Please enter your email address" is visible in the snapshot.',
  ),
]);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    'Fill the Email Address field with "test@example.com" but leave the Password field empty, then click Sign In.',
    'an error message containing "password" or "Please enter" is visible in the snapshot.',
  ),
]);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    'Fill Email Address with "wrong@test.com" and Password with "wrongpassword", then click Sign In.',
    'an error message is visible (e.g. "Invalid email or password", "Login failed", "Too many login attempts", or similar).',
  ),
]);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    'Click the "Forgot password?" button.',
    'heading "Reset Your Password" or a password reset form is visible.',
  ),
]);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    'Click the "Create account" link or button.',
    'heading "Create an account" or a registration form is visible.',
  ),
]);

shortest(
  [
    ...requireLoginPageSteps,
    ...loginSteps,
    assertPage("Test Dashboard"),
  ],
  authPayload,
);

shortest(
  [
    ...loginSteps,
    assertPage("Test Dashboard"),
    ...logoutSteps,
  ],
  authPayload,
);
