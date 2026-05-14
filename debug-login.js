const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    try {
        console.log("🎬 Testing login with debugging...\n");

        // Navigate to app
        await page.goto("http://localhost:8080");
        await page.waitForLoadState("domcontentloaded");

        // Fill and submit form
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.fill('input[type="password"]', "Demo1234");
        await page.click('button:has-text("Sign In")');

        // Wait for response
        await page.waitForTimeout(3000);

        // Check localStorage
        const accessToken = await page.evaluate(() => localStorage.getItem("access_token"));
        const user = await page.evaluate(() => localStorage.getItem("user"));

        console.log("Access Token:", accessToken ? "Present" : "Missing");
        console.log("User Data:", user ? "Present" : "Missing");

        if (user) {
            console.log("User Info:", JSON.parse(user).email);
        }

        // Check URL
        console.log("Current URL:", page.url());

        // Screenshot
        await page.screenshot({ path: ".context/debug-login.png" });

        // Keep browser open
        await page.waitForTimeout(5000);
    } catch (error) {
        console.error("Error:", error.message);
    } finally {
        await browser.close();
    }
})();
