import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify test case list panel is visible with + New Test button or empty state",
    "Click + New Test button if visible and verify composer workspace opens",
    "Use search filter and verify list updates or shows No matching test cases",
  ],
  authPayload,
);
