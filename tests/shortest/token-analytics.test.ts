import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Token Analytics page title is visible",
    "Verify analytics charts or forecast section is displayed",
  ],
  authPayload,
);
