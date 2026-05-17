const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Intercept localStorage operations
    await page.addInitScript(() => {
        window.localStorageEvents = [];
        const originalSetItem = window.localStorage.prototype.setItem;
        window.localStorage.prototype.setItem = function (key, value) {
            window.localStorageEvents.push({
                type: "setItem",
                key: key,
                value: value,
                timestamp: new Date().toISOString(),
            });
            return originalSetItem.apply(this, [key, value]);
        };

        const originalGetItem = window.localStorage.prototype.getItem;
        window.localStorage.prototype.getItem = function (key) {
            const value = originalGetItem.apply(this, [key]);
            window.localStorageEvents.push({
                type: "getItem",
                key: key,
                value: value,
                timestamp: new Date().toISOString(),
            });
            return value;
        };
    });

    try {
        console.log("🎬 Debugging Login Redirect Issue...\n");

        // Navigate to login page
        console.log("📍 Step 1: Navigating to login page...");
        await page.goto("http://localhost:8080/#login", { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(1000);
        console.log("✅ Page loaded\n");

        // Fill credentials
        console.log("📝 Step 2: Filling credentials...");
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.fill('input[type="password"]', "Demo1234");
        console.log("✅ Credentials filled\n");

        // Monitor console for errors
        page.on("console", (msg) => {
            const text = msg.text();
            if (text.includes("error") || text.includes("Error") || text.includes("fail")) {
                console.log("🔴 Console:", text);
            }
        });

        // Click login button and wait
        console.log("🚀 Step 3: Clicking login button...");
        await page.click('button:has-text("Sign In")');
        console.log("✅ Button clicked\n");

        // Wait for API response
        console.log("⏳ Waiting for API response...");
        await page.waitForTimeout(3000);
        console.log("✅ Wait completed\n");

        // Wait for API response
        await page.waitForTimeout(2000);

        // Check localStorage events
        console.log("📊 Step 4: Checking localStorage events...");
        const storageEvents = await page.evaluate(() => window.localStorageEvents || []);
        console.log(`Total localStorage operations: ${storageEvents.length}\n`);

        storageEvents.forEach((event, index) => {
            console.log(`  ${index + 1}. ${event.type}("${event.key}")`);
            if (event.value && event.value.length > 50) {
                console.log(`     Value: ${event.value.substring(0, 50)}...`);
            } else if (event.value) {
                console.log(`     Value: ${event.value}`);
            }
            console.log(`     Time: ${event.timestamp}\n`);
        });

        // Check current localStorage state
        console.log("📦 Step 5: Current localStorage state:");
        const currentStorage = await page.evaluate(() => {
            return {
                access_token: localStorage.getItem("access_token"),
                refresh_token: localStorage.getItem("refresh_token"),
                session_token: localStorage.getItem("session_token"),
                user: localStorage.getItem("user"),
            };
        });

        console.log("  - access_token:", currentStorage.access_token ? "Present" : "Missing");
        console.log("  - refresh_token:", currentStorage.refresh_token ? "Present" : "Missing");
        console.log("  - session_token:", currentStorage.session_token ? "Present" : "Missing");
        console.log("  - user:", currentStorage.user ? "Present" : "Missing");
        console.log("");

        // Check current URL
        const currentUrl = page.url();
        console.log("🌐 Step 6: Current URL:", currentUrl);
        console.log("");

        // Check for error messages
        const errorElement = await page.locator(".error-message").first();
        const hasError = await errorElement.count();
        if (hasError > 0) {
            const errorText = await errorElement.textContent();
            console.log("❌ Error message on page:", errorText);
            console.log("");
        }

        // Take screenshot
        await page.screenshot({ path: ".context/test-redirect.png" });
        console.log("📸 Screenshot saved to .context/test-redirect.png\n");

        console.log("⏸️  Keeping browser open for 5 seconds...");
        await page.waitForTimeout(5000);
    } catch (error) {
        console.error("💥 Error:", error.message);
        await page.screenshot({ path: ".context/test-redirect-error.png" });
    } finally {
        await browser.close();
    }
})();
