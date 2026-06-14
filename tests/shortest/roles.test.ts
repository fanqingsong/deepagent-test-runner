import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Role Management heading is visible",
    "Verify roles list or role management table is displayed",
  ],
  authPayload,
);
