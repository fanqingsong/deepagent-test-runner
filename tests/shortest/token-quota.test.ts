import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage, assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPage("Quota Management"),
    assertPageAny("Quota", "Global", "Limit"),
  ],
  authPayload,
);
