import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageAny, assertPageLoaded } from "./helpers/prompts";

shortest(
  [
    assertPageLoaded("Budget Management"),
    assertPageAny("Budget", "Create", "Monthly"),
  ],
  authPayload,
);
