import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#reviews", "Review Management"),
    "Verify Review Management heading is visible",
    "Verify Pending Tests or Pending Suites section is displayed",
  ],
  authPayload,
);
