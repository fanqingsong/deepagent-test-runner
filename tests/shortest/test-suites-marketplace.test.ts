import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest(
  [
    "Verify Test Suite Marketplace heading is visible",
    "Verify marketplace shows suite cards or an empty state message",
  ],
  authPayload,
);
