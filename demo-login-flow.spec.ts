import { test, expect, Page } from "@playwright/test";

/**
 * Demo: User Login Flow
 *
 * This script demonstrates the complete user login process:
 * 1. Navigate to login page
 * 2. Show login form
 * 3. Fill in credentials
 * 4. Submit login
 * 5. Show authenticated dashboard
 */

test.describe("User Login Flow Demo", () => {
    let page: Page;

    test.beforeAll(async ({ browser }) => {
        page = await browser.newPage();
    });

    test.afterAll(async () => {
        await page.close();
    });

    test("Complete login flow demonstration", async () => {
        console.log("🎬 Starting Login Flow Demo...\n");

        // Step 1: Navigate to application
        console.log("📍 Step 1: Navigating to application...");
        await page.goto("http://localhost:8080");
        await page.waitForLoadState("networkidle");
        await page.screenshot({ path: ".context/demo-screenshots/01-homepage.png" });
        console.log("✅ Homepage loaded\n");

        // Step 2: Show login page
        console.log("🔐 Step 2: Accessing login page...");
        await page.waitForSelector('input[type="email"]', { timeout: 5000 });
        await page.screenshot({ path: ".context/demo-screenshots/02-login-page.png" });
        console.log("✅ Login form is visible\n");

        // Step 3: Fill in login credentials
        console.log("📝 Step 3: Filling login credentials...");
        const emailInput = page.locator('input[type="email"]');
        const passwordInput = page.locator('input[type="password"]');

        // Highlight the email field
        await emailInput.evaluate((el: any) => (el.style.border = "3px solid #0f62fe"));
        await page.waitForTimeout(500);

        // Fill email
        await emailInput.fill("admin@example.com");
        await page.screenshot({ path: ".context/demo-screenshots/03-email-filled.png" });
        console.log("   ✉️  Email filled: admin@example.com");

        await page.waitForTimeout(500);

        // Highlight the password field
        await passwordInput.evaluate((el: any) => (el.style.border = "3px solid #0f62fe"));
        await page.waitForTimeout(500);

        // Fill password
        await passwordInput.fill("admin123");
        await page.screenshot({ path: ".context/demo-screenshots/04-password-filled.png" });
        console.log("   ✉️  Password filled: ********\n");

        // Remove highlights
        await emailInput.evaluate((el: any) => (el.style.border = ""));
        await passwordInput.evaluate((el: any) => (el.style.border = ""));

        // Step 4: Submit login
        console.log("🚀 Step 4: Submitting login...");
        const submitButton = page.locator('button:has-text("Sign In")');
        await submitButton.evaluate((el: any) => {
            el.style.backgroundColor = "#0353e9";
            el.style.transform = "scale(1.05)";
        });
        await page.waitForTimeout(500);

        // Click login button
        await submitButton.click();
        await page.screenshot({ path: ".context/demo-screenshots/05-login-submit.png" });
        console.log("   ✅ Login button clicked\n");

        // Step 5: Wait for authentication and redirect
        console.log("⏳ Step 5: Waiting for authentication...");
        try {
            await page.waitForURL(/#dashboard/, { timeout: 5000 });
            await page.waitForLoadState("networkidle");

            await page.screenshot({ path: ".context/demo-screenshots/06-dashboard.png" });
            console.log("✅ Login successful! User redirected to dashboard\n");

            // Show dashboard elements
            console.log("📊 Dashboard elements:");
            const dashboardTitle = await page.locator("h1, h2, .dashboard-title").first().textContent();
            console.log(`   - Title: ${dashboardTitle}\n`);
        } catch (error) {
            // If dashboard doesn't load, show what happened
            await page.screenshot({ path: ".context/demo-screenshots/06-login-result.png" });
            console.log("⚠️  Login attempted - checking result...");

            const url = page.url();
            console.log(`   Current URL: ${url}`);

            // Check if there's an error message
            const errorElement = page.locator('.error-message, [role="alert"]').first();
            if ((await errorElement.count()) > 0) {
                const errorText = await errorElement.textContent();
                console.log(`   Error message: ${errorText}`);
            }
        }

        console.log("🎬 Demo Complete!\n");
        console.log("Screenshots saved to: .context/demo-screenshots/");
        console.log("- 01-homepage.png");
        console.log("- 02-login-page.png");
        console.log("- 03-email-filled.png");
        console.log("- 04-password-filled.png");
        console.log("- 05-login-submit.png");
        console.log("- 06-dashboard.png (or 06-login-result.png if login failed)");
    });
});
