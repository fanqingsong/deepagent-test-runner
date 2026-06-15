import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { actThenAssert, assertPageAny } from "../helpers/prompts";

shortest(
  [
    assertPageAny("+ New Suite", "suite", "No suites"),
    actThenAssert(
      'If a "+ New Suite" button is visible, click it.',
      "a suite composer workspace or new suite form is open.",
    ),
  ],
  authPayload,
);
