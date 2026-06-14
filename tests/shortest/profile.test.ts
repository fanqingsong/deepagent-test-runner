import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify My Profile heading is visible",
    "Verify Username and Email fields are displayed on profile form",
  ],
  authPayload,
);
