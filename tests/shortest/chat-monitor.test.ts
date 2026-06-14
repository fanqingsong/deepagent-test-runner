import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#chat-monitor", "Chat Monitor"),
    "Verify Chat Monitor page shows h2 title, Active Sessions stat, or session list panel",
  ],
  authPayload,
);
