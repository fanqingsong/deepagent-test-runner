import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Review Management heading is visible",
    "Verify Pending Tests or Pending Suites section is displayed",
  ],
  authPayload,
);
