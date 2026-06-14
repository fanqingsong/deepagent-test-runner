import { shortest } from "@antiwork/shortest";
import { authPayload, loginSteps, logoutSteps, requireLoginPageSteps } from "./helpers/flows";
import { actThenAssert, assertPage } from "./helpers/prompts";

shortest(
  assertPage("AI Test Runner", "Email Address", "Password", "Sign In"),
);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    "Leave Email Address empty, click Sign In.",
    'an error message such as "Please enter your email address" is visible.',
  ),
]);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    "Fill Email Address with test@example.com, leave Password empty, click Sign In.",
    'an error message such as "Please enter your password" is visible.',
  ),
]);

shortest([
  ...requireLoginPageSteps,
  actThenAssert(
    'Fill Email Address with wrong@test.com and Password with wrongpassword, click Sign In.',
    "an error message about invalid credentials or login failure is visible.",
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
