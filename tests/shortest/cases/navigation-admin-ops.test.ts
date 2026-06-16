import { shortest } from "@antiwork/shortest";
import { authPayload, navAndVerify } from "../helpers/flows";

type Route = [hash: string, title: string, ...matchTexts: string[]];

const routes: Route[] = [
  ["#chat-monitor", "Chat Monitor", "Chat Monitor", "7d"],
  ["#monitoring", "System Monitoring", "System Monitoring", "Alerts"],
];

for (const [hash, title, ...texts] of routes) {
  shortest([navAndVerify(hash, title, ...texts)], authPayload);
}
