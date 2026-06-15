import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPageAny, assertPageLoaded } from "../helpers/prompts";

shortest(
  [
    assertPageLoaded("User Management"),
    assertPageAny("Create User", "Users", "user"),
  ],
  authPayload,
);
