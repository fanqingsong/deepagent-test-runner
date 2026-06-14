import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify System Monitoring heading is visible",
    "Verify AI Analysis or Alerts section is displayed",
  ],
  authPayload,
);
