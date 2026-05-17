const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Capture all network requests
    page.on("request", (request) => {
        if (request.url().includes("/api/v1/auth/login")) {
            console.log("🔵 Request:", request.method(), request.url());
            console.log("   Headers:", JSON.stringify(request.headers(), null, 2));
            try {
                console.log("   Body:", request.postData());
            } catch (e) {
                console.log("   Body: (Cannot read)");
            }
        }
    });

    page.on("response", async (response) => {
        if (response.url().includes("/api/v1/auth/login")) {
            console.log("🟢 Response:", response.status(), response.url());
            console.log("   Headers:", JSON.stringify(response.headers(), null, 2));

            try {
                const body = await response.text();
                console.log("   Response Body:", body);

                // Try to parse as JSON
                try {
                    const jsonBody = JSON.parse(body);
                    console.log("   Parsed JSON:", JSON.stringify(jsonBody, null, 2));

                    // Check for tokens
                    if (jsonBody.access_token) {
                        console.log("   ✅ access_token present:", jsonBody.access_token.substring(0, 20) + "...");
                    } else {
                        console.log("   ❌ access_token MISSING");
                    }

                    if (jsonBody.refresh_token) {
                        console.log("   ✅ refresh_token present");
                    } else {
                        console.log("   ❌ refresh_token MISSING");
                    }

                    if (jsonBody.session_token) {
                        console.log("   ✅ session_token present");
                    } else {
                        console.log("   ❌ session_token MISSING");
                    }

                    if (jsonBody.user) {
                        console.log("   ✅ user present:", jsonBody.user.email);
                    } else {
                        console.log("   ❌ user MISSING");
                    }

                    if (jsonBody.require_mfa) {
                        console.log("   ⚠️  MFA REQUIRED");
                    }
                } catch (parseError) {
                    console.log("   (Not JSON)");
                }
            } catch (e) {
                console.log("   (Cannot read response body)");
            }
        }
    });

    // Capture console errors
    page.on("console", (msg) => {
        const text = msg.text();
        if (text.toLowerCase().includes("error") || text.toLowerCase().includes("fail")) {
            console.log("🔴 Console:", text);
        }
    });

    // Capture page errors
    page.on("pageerror", (error) => {
        console.log("💥 Page Error:", error.message);
        console.log("   Stack:", error.stack);
    });

    try {
        console.log("🎬 Debugging Network Response...\n");

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

        // Click login button
        console.log("🚀 Step 3: Clicking login button...");
        await page.click('button:has-text("Sign In")');
        console.log("✅ Button clicked\n");

        // Wait for response
        console.log("⏳ Waiting for network response...");
        await page.waitForTimeout(5000);
        console.log("✅ Wait completed\n");

        // Check final state
        const finalUrl = page.url();
        console.log("🌐 Final URL:", finalUrl);

        const currentStorage = await page.evaluate(() => {
            return {
                access_token: localStorage.getItem("access_token"),
                refresh_token: localStorage.getItem("refresh_token"),
                session_token: localStorage.getItem("session_token"),
                user: localStorage.getItem("user"),
            };
        });

        console.log("📦 localStorage state:");
        console.log("  - access_token:", currentStorage.access_token ? "Present" : "Missing");
        console.log("  - refresh_token:", currentStorage.refresh_token ? "Present" : "Missing");
        console.log("  - session_token:", currentStorage.session_token ? "Present" : "Missing");
        console.log("  - user:", currentStorage.user ? "Present" : "Missing");

        // Check for error messages
        const errorElement = await page.locator(".error-message").first();
        const hasError = await errorElement.count();
        if (hasError > 0) {
            const errorText = await errorElement.textContent();
            console.log("❌ Error message on page:", errorText);
        }

        // Screenshot
        await page.screenshot({ path: ".context/test-network-response.png" });
        console.log("\n📸 Screenshot saved to .context/test-network-response.png");

        console.log("\n⏸️  Keeping browser open for 5 seconds...");
        await page.waitForTimeout(5000);
    } catch (error) {
        console.error("💥 Script Error:", error.message);
        await page.screenshot({ path: ".context/test-network-response-error.png" });
    } finally {
        await browser.close();
    }
})();
