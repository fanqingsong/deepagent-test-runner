import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageAny, assertPageLoaded } from "./helpers/prompts";

shortest(
  [
    assertPageLoaded("My Profile"),
    assertPageAny("Edit Profile", "admin@example.com", "admin"),
  ],
  authPayload,
);
