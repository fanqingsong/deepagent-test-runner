const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    try {
        console.log("🎬 Starting Login Flow Demo with CORRECT credentials...\n");

        // Step 1: Navigate to application
        console.log("📍 Step 1: Navigating to application...");
        await page.goto("http://localhost:8080/#login", { timeout: 10000 });
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

        // Fill email
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.screenshot({ path: ".context/demo-correct/03-email-filled.png" });
        console.log("   ✉️  Email filled: demotest@example.com");

        // Fill password
        await page.fill('input[type="password"]', "Demo1234");
        await page.screenshot({ path: ".context/demo-correct/04-password-filled.png" });
        console.log("   ✉️  Password filled: ********\n");

        // Step 4: Submit login
        console.log("🚀 Step 4: Submitting login...");
        await page.click('button:has-text("Sign In")');
        await page.screenshot({ path: ".context/demo-correct/05-login-submit.png" });
        console.log("   ✅ Login button clicked\n");

        // Step 5: Wait for authentication and redirect
        console.log("⏳ Step 5: Waiting for authentication...");
        await page.waitForTimeout(3000);

        const url = page.url();
        console.log(`   Current URL: ${url}\n`);

        if (url.includes("#dashboard")) {
            await page.screenshot({ path: ".context/demo-correct/06-dashboard.png" });
            console.log("✅ Login successful! User redirected to dashboard\n");

            // Show dashboard elements
            console.log("📊 Dashboard elements:");
            const title = await page.locator("h1, h2").first().textContent();
            console.log(`   - Title: ${title}\n`);
        } else {
            await page.screenshot({ path: ".context/demo-correct/06-login-result.png" });

            // Check for error message
            const errorElement = page.locator(".error-message").first();
            const hasError = await errorElement.count();

            if (hasError > 0) {
                const errorText = await errorElement.textContent();
                console.log(`⚠️  Error message: ${errorText}\n`);
            } else {
                console.log("ℹ️  Login completed, but no dashboard redirect\n");
            }
        }

        console.log("🎬 Demo Complete!");
        console.log("Screenshots saved to: .context/demo-correct/");

        // Keep browser open for viewing
        console.log("\n⏸️  Keeping browser open for 5 seconds...");
        await page.waitForTimeout(5000);
    } catch (error) {
        console.error("❌ Error:", error.message);
        await page.screenshot({ path: ".context/demo-correct/error.png" });
    } finally {
        await browser.close();
    }
})();
