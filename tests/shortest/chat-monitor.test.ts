import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Chat Monitor page shows h2 title, Active Sessions stat, or session list panel",
  ],
  authPayload,
);
