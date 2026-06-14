import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#token-quota", "Quota Management"),
    "Verify Quota Management page title is visible",
    "Verify global quota configuration section is displayed",
  ],
  authPayload,
);
