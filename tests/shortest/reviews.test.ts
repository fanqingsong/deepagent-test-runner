import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage, assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPage("Review Management"),
    assertPageAny("Pending Tests", "Pending Suites", "pending", "No pending"),
  ],
  authPayload,
);
