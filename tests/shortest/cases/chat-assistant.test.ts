import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { actThenAssert } from "../helpers/prompts";

shortest(
  [
    actThenAssert(
      'If a chat message textbox is not visible, click the button with aria-label "Open chat".',
      'a message textbox or chat input area is visible in the snapshot.',
    ),
    actThenAssert(
      'Close the chat panel by clicking the button with aria-label "Close chat", or press Escape.',
      'the button with aria-label "Open chat" is visible again.',
    ),
  ],
  authPayload,
);
