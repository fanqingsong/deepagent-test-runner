import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage, assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPage("Budget Management"),
    assertPageAny("Budget", "Create", "Monthly"),
  ],
  authPayload,
);
