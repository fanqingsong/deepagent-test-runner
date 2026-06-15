import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { actThenAssert } from "../helpers/prompts";

// Token Analytics route crashes in headless; verify the sidebar entry is reachable.
shortest(
  [
    actThenAssert(
      'If the sidebar is collapsed, click "Expand sidebar" or "Toggle menu" to open it.',
      'the snapshot contains "Token Management" or "Token Analytics".',
    ),
  ],
  authPayload,
);
