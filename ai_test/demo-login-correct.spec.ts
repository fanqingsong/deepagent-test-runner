import { test } from "@playwright/test";

/**
 * Demo: User Login Flow with CORRECT Credentials
 *
 * Test credentials:
 * - Email: demotest@example.com
 * - Password: Demo1234
 */

test("Complete login flow demonstration", async ({ page }) => {
    console.log("🎬 Starting Login Flow Demo...\n");

    // Step 1: Navigate to application
    console.log("📍 Step 1: Navigating to application...");
    await page.goto("http://localhost:8080");
    await page.waitForLoadState("domcontentloaded");
    await page.screenshot({ path: ".context/demo-correct/01-homepage.png" });
    console.log("✅ Homepage loaded\n");

    // Step 2: Show login page
    console.log("🔐 Step 2: Accessing login page...");
    await page.waitForSelector('input[type="email"]', { timeout: 5000 });
    await page.screenshot({ path: ".context/demo-correct/02-login-page.png" });
    console.log("✅ Login form is visible\n");

    // Step 3: Fill in login credentials
    console.log("📝 Step 3: Filling login credentials...");
    const emailInput = page.locator('input[type="email"]');
    const passwordInput = page.locator('input[type="password"]');

    // Fill email
    await emailInput.fill("demotest@example.com");
    await page.screenshot({ path: ".context/demo-correct/03-email-filled.png" });
    console.log("   ✉️  Email filled: demotest@example.com");

    // Fill password
    await passwordInput.fill("Demo1234");
    await page.screenshot({ path: ".context/demo-correct/04-password-filled.png" });
    console.log("   ✉️  Password filled: ********\n");

    // Step 4: Submit login
    console.log("🚀 Step 4: Submitting login...");
    const submitButton = page.locator('button:has-text("Sign In")');
    await submitButton.click();
    await page.screenshot({ path: ".context/demo-correct/05-login-submit.png" });
    console.log("   ✅ Login button clicked\n");

    // Step 5: Wait for authentication and redirect
    console.log("⏳ Step 5: Waiting for authentication...");
    try {
        await page.waitForURL(/#dashboard/, { timeout: 5000 });
        await page.waitForLoadState("networkidle");

        await page.screenshot({ path: ".context/demo-correct/06-dashboard.png" });
        console.log("✅ Login successful! User redirected to dashboard\n");

        // Show dashboard elements
        console.log("📊 Dashboard elements:");
        const dashboardTitle = await page.locator("h1, h2, .dashboard-title").first().textContent();
        console.log(`   - Title: ${dashboardTitle}\n`);
    } catch (error) {
        // If dashboard doesn't load, show what happened
        await page.screenshot({ path: ".context/demo-correct/06-login-result.png" });
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
    console.log("Screenshots saved to: .context/demo-correct/");
});
