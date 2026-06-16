import { shortest } from "@antiwork/shortest";
import { authPayload, navAndVerify } from "../helpers/flows";

type Route = [hash: string, title: string, ...matchTexts: string[]];

const routes: Route[] = [
  ["#token-quota", "Quota Management", "Quota Management", "Quota"],
  ["#token-alert", "Alert Management", "Alert Management", "Alert"],
];

for (const [hash, title, ...texts] of routes) {
  shortest([navAndVerify(hash, title, ...texts)], authPayload);
}
