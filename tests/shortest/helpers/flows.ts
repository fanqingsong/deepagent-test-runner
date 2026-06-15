import { E2E_CREDENTIALS } from "./credentials";

/** Credentials payload passed to shortest() for login steps */
export const authPayload = {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
};

/** Fresh login from unauthenticated state */
export const loginSteps = [
  "Call browser_snapshot. Fill the Email Address field with the provided email and the Password field with the provided password, then click the Sign In button.",
];

/** Ensure login form is visible (logout first if authenticated, navigate to login if on another form) */
export const requireLoginPageSteps = [
  "If a user menu or avatar in the header indicates a logged-in session, open it and click Logout. If the snapshot does not show the main login form with Email Address, Password, and Sign In, use the navigate tool to open http://localhost:8085/#login.",
  'Call browser_snapshot. Pass if heading "AI Test Runner", field "Email Address", field "Password", and button "Sign In" are all visible.',
];

export const logoutSteps = [
  "Open the user menu in the header and click Logout",
  'Call browser_snapshot. Pass if heading "AI Test Runner" and button "Sign In" are visible.',
];

/** Navigate with shortest navigate tool (navigation.test.ts only). */
export function goTo(hash: string, pageTitle: string): string {
  const path = hash.startsWith("#") ? hash : `#${hash}`;
  const base = (process.env.BASE_URL || "http://localhost:8085").replace(/\/$/, "");
  const marketplaceHint =
    hash === "#test-cases-marketplace"
      ? ' After navigation, expand "Test Cases" in the sidebar and click "Marketplace" if the page did not change.'
      : hash === "#suites-marketplace"
        ? ' After navigation, expand "Test Suites" in the sidebar and click "Marketplace" if the page did not change.'
        : "";
  return `Use the navigate tool to open exactly "${base}${path}".${marketplaceHint} Call browser_snapshot. If "${pageTitle}" is not in the main content, wait 2 seconds and snapshot again. Pass when "${pageTitle}" appears.`;
}
