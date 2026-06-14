import { shortest } from "@antiwork/shortest";
import { authPayload, goTo } from "./helpers/flows";

shortest(
  [
    goTo("#nanjing-weather", "Nanjing Weather"),
    "Verify Nanjing weather page heading containing 天气 is visible",
    "Verify current weather information or loading state is displayed",
  ],
  authPayload,
);
