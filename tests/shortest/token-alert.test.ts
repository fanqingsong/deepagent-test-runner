import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#token-alert", "Alert Management"),
    "Verify Alert Management page title is visible",
    "Verify alert configuration or alert list section is displayed",
  ],
  authPayload,
);
