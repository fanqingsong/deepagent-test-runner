import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Budget Management page title is visible",
    "Verify budget list or create budget UI is displayed",
  ],
  authPayload,
);
