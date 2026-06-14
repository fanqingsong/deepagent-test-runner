import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Nanjing weather page heading containing 天气 is visible",
    "Verify current weather information or loading state is displayed",
  ],
  authPayload,
);
