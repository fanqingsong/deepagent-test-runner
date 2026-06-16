import { E2E_CREDENTIALS } from "./credentials";

/** Credentials payload passed to shortest() for login steps */
export const authPayload = {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
};

/** Fresh login from unauthenticated state */
export const loginSteps = [
  "Navigate to http://localhost:8085/#login if the Sign In form is not visible.",
  "Fill Email Address with the provided email and Password with the provided password, then click Sign In and wait until loading finishes.",
];

/** Ensure login form is visible (logout first if authenticated, navigate to login if on another form) */
export const openLoginFormSteps = [
  "Call browser_snapshot. If Email Address, Password, and Sign In are not visible, use the navigate tool to open http://localhost:8085/#login.",
];

export const requireLoginPageSteps = [
  "If a user menu or avatar indicates a logged-in session, open it and click Logout.",
  "If Email Address, Password, and Sign In are not visible, use the navigate tool to open http://localhost:8085/#login.",
];

export const logoutSteps = [
  "Open the user menu in the header and click Logout",
  'Call browser_snapshot. Pass if heading "AI Test Runner" and button "Sign In" are visible.',
];

const SIDEBAR_FALLBACKS: Record<string, string> = {
  "#test-cases-marketplace":
    ' If the page did not change, expand "Test Cases" in the sidebar and click "Marketplace".',
  "#suites-marketplace":
    ' If the page did not change, expand "Test Suites" in the sidebar and click "Marketplace".',
  "#token-usage":
    ' If the page did not change, expand "Token Management" in the sidebar and click "Usage Dashboard".',
  "#token-budget":
    ' If the page did not change, expand "Token Management" in the sidebar and click "Budget Management".',
  "#token-quota":
    ' If the page did not change, expand "Token Management" in the sidebar and click "Quota Management".',
  "#token-alert":
    ' If the page did not change, expand "Token Management" in the sidebar and click "Alert Management".',
  "#profile":
    ' If the page did not change, expand "System Management" in the sidebar and click "My Profile".',
  "#users":
    ' If the page did not change, expand "System Management" in the sidebar and click "User Management".',
  "#roles":
    ' If the page did not change, expand "System Management" in the sidebar and click "Role Management".',
  "#reviews":
    ' If the page did not change, expand "System Management" in the sidebar and click "Review Management".',
  "#chat-monitor":
    ' If the page did not change, expand "System Management" in the sidebar and click "Chat Monitor".',
  "#monitoring":
    ' If the page did not change, expand "System Management" in the sidebar and click "System Monitoring".',
};

/** Navigate and verify in one step (avoids losing page state between steps). */
export function navAndVerify(hash: string, pageTitle: string, ...matchTexts: string[]): string {
  const path = hash.startsWith("#") ? hash : `#${hash}`;
  const base = (process.env.BASE_URL || "http://localhost:8085").replace(/\/$/, "");
  const texts = matchTexts.length > 0 ? matchTexts : [pageTitle];
  const sidebarHint = SIDEBAR_FALLBACKS[path] ?? "";
  return `Use the navigate tool to open exactly "${base}${path}". Call browser_snapshot. If the expected content is missing, click "Expand sidebar" or "Toggle menu" if visible, then snapshot again.${sidebarHint} If still missing, wait 2 seconds and snapshot again. Pass when the snapshot contains at least one of: ${texts.map((t) => `"${t}"`).join(", ")}.`;
}
