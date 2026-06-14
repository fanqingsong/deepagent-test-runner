import { E2E_CREDENTIALS } from "./credentials";

/** Credentials payload passed to shortest() for login steps */
export const authPayload = {
  email: E2E_CREDENTIALS.email,
  password: E2E_CREDENTIALS.password,
};

/** Fresh login from unauthenticated state */
export const loginSteps = [
  "Open the app login page",
  "Enter the provided email and password credentials into the login form, then click Sign In",
];

/** Ensure login form is visible (logout first if authenticated) */
export const requireLoginPageSteps = [
  "If logged in, open user dropdown in header and click Logout",
  "Verify login page with Sign In form and email/password fields is visible",
];

export const logoutSteps = [
  "Open user dropdown in header and click Logout",
  "Verify login page is shown again",
];

/** Navigate via URL hash (faster and more reliable than AI sidebar clicks). */
export function goTo(hash: string, _label: string): string {
  const path = hash.startsWith("#") ? hash : `#${hash}`;
  return `Navigate directly to URL hash ${path} and wait for the page to finish loading`;
}
