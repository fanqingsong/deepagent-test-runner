import { shortest } from "@antiwork/shortest";
import { authPayload, goTo, loginSteps } from "./helpers/flows";

shortest([...loginSteps, "Verify Test Dashboard heading is visible"], authPayload);

shortest([
  ...loginSteps,
  "Verify Admin View or Personal View badge is visible on dashboard",
], authPayload);

shortest([
  ...loginSteps,
  "Verify time range buttons 7 days, 30 days, and 90 days are visible",
], authPayload);

shortest([
  ...loginSteps,
  goTo("#dashboard", "Dashboard"),
  "Verify LLM usage stats section or summary cards are visible",
], authPayload);
