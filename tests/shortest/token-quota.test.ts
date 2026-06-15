import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageAny, assertPageLoaded } from "./helpers/prompts";

shortest(
  [
    assertPageLoaded("Quota Management"),
    assertPageAny("Quota", "Global", "Limit"),
  ],
  authPayload,
);
