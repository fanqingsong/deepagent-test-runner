import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    "Verify Test Dashboard heading is visible",
    "Verify Admin View or Personal View badge is visible on dashboard",
    "Verify time range buttons 7 days, 30 days, and 90 days are visible",
  ],
  authPayload,
);
