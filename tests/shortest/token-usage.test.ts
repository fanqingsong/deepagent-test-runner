import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage, assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPage("Token Usage Dashboard"),
    assertPageAny("Tokens", "Usage", "Total"),
  ],
  authPayload,
);
