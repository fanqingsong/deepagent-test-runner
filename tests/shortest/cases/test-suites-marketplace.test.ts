import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPageAny, assertPageLoaded } from "../helpers/prompts";

shortest(
  [
    assertPageLoaded("Test Suite Marketplace"),
    assertPageAny("suite", "empty", "No suites", "Marketplace"),
  ],
  authPayload,
);
