import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage } from "./helpers/prompts";

shortest(
  [
    assertPage("Test Dashboard"),
    assertPageAny("Admin View", "Personal View"),
    assertPage("7 days", "30 days", "90 days"),
  ],
  authPayload,
);
