import { shortest } from "@antiwork/shortest";
import { openLoginFormSteps } from "../helpers/flows";
import { actThenAssert } from "../helpers/prompts";

shortest([
  ...openLoginFormSteps,
  actThenAssert(
    'Navigate to http://localhost:8085/#login. Fill Email "wrong@test.com" and Password "wrongpassword", click Sign In, wait 3 seconds.',
    '"Test Dashboard" is not in the snapshot and the Sign In form or a login error alert is still visible',
  ),
]);
