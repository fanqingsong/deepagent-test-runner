import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageAny, assertPageLoaded } from "./helpers/prompts";

shortest(
  [
    assertPageLoaded("Alert Management"),
    assertPageAny("Alert", "Create", "Active"),
  ],
  authPayload,
);
