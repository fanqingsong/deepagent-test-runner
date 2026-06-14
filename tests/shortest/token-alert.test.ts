import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Alert Management page title is visible",
    "Verify alert configuration or alert list section is displayed",
  ],
  authPayload,
);
