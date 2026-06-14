import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify User Management heading is visible",
    "Verify user list table is displayed",
    "Click Create User button if visible and verify create user modal opens",
  ],
  authPayload,
);
