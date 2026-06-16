import { shortest } from "@antiwork/shortest";
import { openLoginFormSteps } from "../helpers/flows";
import { actThenAssert } from "../helpers/prompts";

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    'Fill Email Address with "wrong@test.com" and Password with "wrongpassword", then click Sign In.',
    'the snapshot still shows the Sign In form and does not contain "Test Dashboard" (an error like "Invalid email or password" may appear).',
  ),
]);
