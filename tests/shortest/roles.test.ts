import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage, assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPage("Role Management"),
    assertPageAny("role", "Role", "Permissions"),
  ],
  authPayload,
);
