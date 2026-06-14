import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#suites", "Test Suites My Workspace"),
    "Verify suite list panel is visible with + New Suite button or empty state",
    "Click + New Suite button and verify suite composer workspace opens",
    "Use search filter and verify list updates or shows No matching test suites",
  ],
  authPayload,
);
