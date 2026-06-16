import { shortest } from "@antiwork/shortest";
import { authPayload, navAndVerify } from "../helpers/flows";

shortest(
  [navAndVerify("#token-budget", "Budget Management", "Budget Management", "Budget", "Monthly")],
  authPayload,
);
