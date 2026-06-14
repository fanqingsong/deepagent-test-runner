import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Quota Management page title is visible",
    "Verify global quota configuration section is displayed",
  ],
  authPayload,
);
