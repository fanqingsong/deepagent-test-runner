import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPage, assertPageAny } from "../helpers/prompts";

shortest(
  [
    assertPage("Test Case Marketplace"),
    assertPageAny("test case", "empty", "No test cases"),
  ],
  authPayload,
);
