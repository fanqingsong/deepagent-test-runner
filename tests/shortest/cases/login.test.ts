import { shortest } from "@antiwork/shortest";
import { authPayload, logoutSteps, openLoginFormSteps } from "../helpers/flows";
import { actThenAssert, assertPage } from "../helpers/prompts";

shortest(assertPage("AI Test Runner", "Email Address", "Password", "Sign In"));

shortest(
  [
    ...openLoginFormSteps,
    actThenAssert(
      "Fill Email Address with provided email and Password with provided password, then click Sign In and wait 3 seconds.",
      '"Test Dashboard" is in the snapshot',
    ),
    ...logoutSteps,
  ],
  authPayload,
);
