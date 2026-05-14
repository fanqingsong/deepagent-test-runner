const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Capture console errors
    page.on("console", (msg) => {
        if (msg.type() === "error") {
            console.log("Browser Error:", msg.text());
        }
    });

    // Capture network failures
    page.on("response", (response) => {
        if (response.status() >= 400) {
            console.log(`HTTP ${response.status()}:`, response.url());
        }
    });

    try {
        console.log("🎬 Testing login with console capture...\n");

        // Navigate to app
        await page.goto("http://localhost:8080");
        await page.waitForLoadState("domcontentloaded");

        // Fill and submit form
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.fill('input[type="password"]', "Demo1234");

        console.log("Submitting login...");
        await page.click('button:has-text("Sign In")');

        // Wait for response
        await page.waitForTimeout(5000);

        // Check state
        const accessToken = await page.evaluate(() => localStorage.getItem("access_token"));
        const userStr = await page.evaluate(() => localStorage.getItem("user"));
        const url = page.url();

        console.log("\nFinal State:");
        console.log("- URL:", url);
        console.log("- Access Token:", accessToken ? "Present" : "Missing");
        console.log("- User:", userStr ? JSON.parse(userStr).email : "Missing");

        // Check for error messages on page
        const errorElement = await page.locator(".error-message").first();
        if ((await errorElement.count()) > 0) {
            const errorText = await errorElement.textContent();
            console.log("- Page Error:", errorText);
        }

        // Screenshot
        await page.screenshot({ path: ".context/debug-console.png" });

        // Keep browser open for viewing
        await page.waitForTimeout(5000);
    } catch (error) {
        console.error("Script Error:", error.message);
    } finally {
        await browser.close();
    }
})();
