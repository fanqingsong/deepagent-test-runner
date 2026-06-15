import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPage, assertPageAny } from "../helpers/prompts";

shortest(
  [
    assertPage("System Monitoring"),
    assertPageAny("AI Analysis", "Alerts"),
  ],
  authPayload,
);
