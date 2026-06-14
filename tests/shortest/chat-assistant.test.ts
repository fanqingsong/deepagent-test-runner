import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { actThenAssert, assertPage } from "./helpers/prompts";

shortest(
  [
    actThenAssert(
      'Click the button with aria-label "Open chat" in the bottom-right corner.',
      'the chat panel or modal is open and a message textbox or input area is visible.',
    ),
    actThenAssert(
      'Click the button with aria-label "Close chat".',
      'the button with aria-label "Open chat" is visible again and the chat modal is closed.',
    ),
  ],
  authPayload,
);
