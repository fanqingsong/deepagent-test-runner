import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPageAny, assertPageLoaded } from "../helpers/prompts";

shortest(
  [
    assertPageLoaded("System Monitoring"),
    assertPageAny("AI Analysis", "Alerts", "Monitoring"),
  ],
  authPayload,
);
