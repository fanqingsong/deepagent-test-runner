import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#users", "User Management"),
    "Verify User Management heading is visible",
    "Verify user list table is displayed",
    "Click Create User button if visible and verify create user modal opens",
  ],
  authPayload,
);
