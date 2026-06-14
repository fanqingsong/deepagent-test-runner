import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#monitoring", "System Monitoring"),
    "Verify System Monitoring heading is visible",
    "Verify AI Analysis or Alerts section is displayed",
  ],
  authPayload,
);
