import { shortest } from "@antiwork/shortest";
import { openLoginFormSteps } from "../helpers/flows";
import { actThenAssert } from "../helpers/prompts";

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    'Navigate to http://localhost:8085/#login, then click "Forgot password?".',
    'heading "Reset Your Password" or a reset email form is visible',
  ),
]);

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    'Navigate to http://localhost:8085/#login, then click "Create account".',
    'heading "Create an account" or a registration form is visible',
  ),
]);
