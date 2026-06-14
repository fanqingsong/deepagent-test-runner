import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage, assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPage("Test Suite Marketplace"),
    assertPageAny("suite", "empty", "No suites"),
  ],
  authPayload,
);
