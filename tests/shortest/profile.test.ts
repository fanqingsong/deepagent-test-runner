import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#profile", "My Profile"),
    "Verify My Profile heading is visible",
    "Verify Username and Email fields are displayed on profile form",
  ],
  authPayload,
);
