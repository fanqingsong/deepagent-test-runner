import { shortest } from "@antiwork/shortest";
import { openLoginFormSteps } from "../helpers/flows";
import { actThenAssert } from "../helpers/prompts";

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    "Click Sign In without filling any fields.",
    'the snapshot shows an email validation error (e.g. "Please enter your email address", "Email Address required", or browser required-field hint)',
  ),
]);

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    'Navigate to http://localhost:8085/#login, then type "test@example.com" into Email Address only and click Sign In.',
    'the snapshot shows a password validation error (e.g. "Please enter your password", "Password required", or browser required-field hint)',
  ),
]);
