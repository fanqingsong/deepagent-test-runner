import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(["Verify Test Dashboard heading is visible"], authPayload);
