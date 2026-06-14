import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#token-budget", "Budget Management"),
    "Verify Budget Management page title is visible",
    "Verify budget list or create budget UI is displayed",
  ],
  authPayload,
);
