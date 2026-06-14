import { shortest } from "@antiwork/shortest";
import { authPayload } from "./helpers/flows";

shortest("Open the login page and verify AI Test Runner heading and Sign In form with email and password fields");

shortest("Sign in with valid email and password", authPayload);

shortest("Try to sign in with empty email and verify an error message appears");

shortest("Try to sign in with empty password and verify an error message appears");

shortest("Try invalid credentials wrong@test.com / wrongpassword and verify an error message appears");

shortest('Click "Forgot password?" and verify Reset Your Password form is shown');

shortest('Click "Create account" and verify registration form is shown');

shortest([
  "Sign in with valid email and password",
  "Verify Test Dashboard heading is visible",
  "Open user dropdown in header and click Logout",
  "Verify login page is shown again",
], authPayload);
