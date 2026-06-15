import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageAny, assertPageLoaded } from "./helpers/prompts";

shortest(
  [
    assertPageLoaded("Token Usage Dashboard"),
    assertPageAny("Tokens", "Usage", "Total"),
  ],
  authPayload,
);
