import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageAny } from "./helpers/prompts";

shortest(
  [
    assertPageAny("天气", "Nanjing", "Weather"),
    assertPageAny("°", "℃", "更新", "Loading", "Weather Information"),
  ],
  authPayload,
);
