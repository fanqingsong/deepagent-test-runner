import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Token Usage Dashboard heading is visible",
    "Verify token usage summary cards or charts are displayed",
  ],
  authPayload,
);
