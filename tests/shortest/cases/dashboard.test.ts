import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPageLoaded } from "../helpers/prompts";

shortest([assertPageLoaded("Test Dashboard", "7 days", "30 days", "90 days")], authPayload);
