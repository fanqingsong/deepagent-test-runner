import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage } from "./helpers/prompts";

shortest(
  [
    assertPage("My Profile"),
    assertPage("Username", "Email"),
  ],
  authPayload,
);
