import { shortest } from "@antiwork/shortest";
import { authPayload, navAndVerify } from "../helpers/flows";

shortest(
  [navAndVerify("#token-usage", "Token Usage Dashboard", "Token Usage Dashboard", "Total Tokens")],
  authPayload,
);
