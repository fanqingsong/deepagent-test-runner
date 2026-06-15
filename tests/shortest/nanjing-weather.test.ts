import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageAny } from "./helpers/prompts";

shortest(
  [assertPageAny("天气", "Weather", "Weather Information", "Loading")],
  authPayload,
);
