import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Click the floating chat button Open chat in bottom-right corner",
    "Verify chat modal opens with message input area",
    "Close the chat modal using close button",
    "Verify chat modal is closed and floating chat button is visible again",
  ],
  authPayload,
);
