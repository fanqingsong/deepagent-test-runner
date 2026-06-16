import { shortest } from "@antiwork/shortest";
import { authPayload, navAndVerify } from "../helpers/flows";

type Route = [hash: string, title: string, ...matchTexts: string[]];

const routes: Route[] = [
  ["#users", "User Management", "User Management", "Create User"],
  ["#roles", "Role Management", "Role Management", "Permissions"],
  ["#reviews", "Review Management", "Review Management"],
];

for (const [hash, title, ...texts] of routes) {
  shortest([navAndVerify(hash, title, ...texts)], authPayload);
}
