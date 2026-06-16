import { shortest } from "@antiwork/shortest";
import { openLoginFormSteps } from "../helpers/flows";
import { actThenAssert } from "../helpers/prompts";

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    'Click the "Forgot password?" link button below the password field.',
    'the snapshot contains "Reset Your Password" or a password reset email form.',
  ),
]);

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    'Click the "Create account" link button in the footer below "Don\'t have an account?".',
    'the snapshot contains "Create an account" or "Create a new account".',
  ),
]);
