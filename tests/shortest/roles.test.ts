import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#roles", "Role Management"),
    "Verify Role Management heading is visible",
    "Verify roles list or role management table is displayed",
  ],
  authPayload,
);
