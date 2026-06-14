import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#token-analytics", "Token Analytics"),
    "Verify Token Analytics page title is visible",
    "Verify analytics charts or forecast section is displayed",
  ],
  authPayload,
);
