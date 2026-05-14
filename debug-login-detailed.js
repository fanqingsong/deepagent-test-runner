const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Enable detailed request/response logging
    page.on("request", (request) => {
        console.log("→ Request:", request.method(), request.url());
    });

    page.on("response", async (response) => {
        const status = response.status();
        const url = response.url();
        console.log("← Response:", status, url);

        if (status >= 400) {
            try {
                const body = await response.text();
                console.log("  Error body:", body.substring(0, 200));
            } catch (e) {
                console.log("  (Cannot read response body)");
            }
        }
    });

    page.on("console", (msg) => {
        const type = msg.type();
        const text = msg.text();
        if (type === "error" || text.toLowerCase().includes("error")) {
            console.log("🔴 Console:", text);
        } else if (type === "warning") {
            console.log("⚠️  Console:", text);
        }
    });

    page.on("pageerror", (error) => {
        console.log("💥 Page Error:", error.message);
    });

    try {
        console.log("🎬 Starting detailed login debugging...\n");

        // Navigate to login page
        console.log("📍 Step 1: Navigating to login page...");
        await page.goto("http://localhost:8080/#login", { waitUntil: "domcontentloaded", timeout: 10000 });
        await page.waitForTimeout(2000);
        console.log("✅ Page loaded\n");

        // Check if form is visible
        const emailVisible = await page.locator('input[type="email"]').isVisible();
        const passVisible = await page.locator('input[type="password"]').isVisible();
        const buttonVisible = await page.locator('button:has-text("Sign In")').isVisible();

        console.log("Form elements visible:");
        console.log("  - Email input:", emailVisible);
        console.log("  - Password input:", passVisible);
        console.log("  - Sign In button:", buttonVisible);
        console.log("");

        // Fill form
        console.log("📝 Step 2: Filling credentials...");
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.fill('input[type="password"]', "Demo1234");
        console.log("✅ Credentials filled\n");

        // Check button state before click
        const buttonBefore = await page.locator('button:has-text("Sign In")');
        const disabledBefore = await buttonBefore.isDisabled();
        console.log("Button state before click:");
        console.log("  - Disabled:", disabledBefore);
        console.log("  - Visible:", await buttonBefore.isVisible());
        console.log("");

        // Click login button
        console.log("🚀 Step 3: Clicking Sign In button...");
        await buttonBefore.click();
        console.log("✅ Button clicked\n");

        // Wait and observe
        console.log("⏳ Step 4: Waiting for response (10 seconds)...");

        // Check loading state
        for (let i = 1; i <= 10; i++) {
            await page.waitForTimeout(1000);

            const button = page.locator('button:has-text("Sign In")');
            const disabled = await button.isDisabled();
            const loadingText = await page.locator('button:has-text("Creating account..."), "button:has-text("Logging in...")').count();

            console.log(`  [${i}s] Button disabled: ${disabled}, Loading indicators: ${loadingText}`);

            // Check if URL changed
            const url = page.url();
            if (!url.includes("#login")) {
                console.log(`\n✅ URL changed to: ${url}`);
                break;
            }

            // Check for error message
            const error = page.locator(".error-message");
            if ((await error.count()) > 0) {
                const errorText = await error.textContent();
                console.log(`\n❌ Error message: ${errorText}`);
                break;
            }

            // Check if reached dashboard
            if (url.includes("#dashboard")) {
                console.log("\n✅ Successfully redirected to dashboard!");
                break;
            }
        }

        // Final state check
        const finalUrl = page.url();
        const accessToken = await page.evaluate(() => localStorage.getItem("access_token"));
        const user = await page.evaluate(() => localStorage.getItem("user"));

        console.log("\n📊 Final State:");
        console.log("  - URL:", finalUrl);
        console.log("  - Access Token:", accessToken ? "Present" : "Missing");
        console.log("  - User:", user ? JSON.parse(user).email : "Missing");

        // Take screenshot
        await page.screenshot({ path: ".context/debug-detailed.png" });

        console.log("\n📸 Screenshot saved to .context/debug-detailed.png");
        console.log("\n⏸️  Keeping browser open for 10 seconds for inspection...");
        await page.waitForTimeout(10000);
    } catch (error) {
        console.error("💥 Script Error:", error.message);
        console.error("Stack:", error.stack);
    } finally {
        await browser.close();
    }
})();
