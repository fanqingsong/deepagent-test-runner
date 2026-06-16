import { shortest } from "@antiwork/shortest";
import { authPayload } from "../helpers/flows";
import { assertPageAny } from "../helpers/prompts";

shortest([assertPageAny("Test Dashboard", "Dashboard")], authPayload);
