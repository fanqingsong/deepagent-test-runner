import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPageLoaded } from "./helpers/prompts";

shortest([assertPageLoaded("Chat Monitor", "7d", "30d")], authPayload);
