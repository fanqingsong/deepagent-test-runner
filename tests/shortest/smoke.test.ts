import { shortest } from "@antiwork/shortest";
import { authPayload, loginSteps } from "./helpers/flows";

shortest([
  ...loginSteps,
  "Verify Test Dashboard heading is visible",
], authPayload);
