import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";
import { assertPage } from "./helpers/prompts";

shortest([assertPage("Chat Monitor", "Active Sessions")], authPayload);
