import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { actThenAssert, assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPageAny("+ New Test", "test case", "No test cases"),
    actThenAssert(
      'If a "+ New Test" button is visible, click it.',
      "a composer workspace or new test form is open.",
    ),
  ],
  authPayload,
);
