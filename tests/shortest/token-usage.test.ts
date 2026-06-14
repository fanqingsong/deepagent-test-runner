import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#token-usage", "Token Usage Dashboard"),
    "Verify Token Usage Dashboard heading is visible",
    "Verify token usage summary cards or charts are displayed",
  ],
  authPayload,
);
