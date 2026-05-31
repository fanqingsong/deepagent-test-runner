const { chromium } = require("playwright");

async function diagnose() {
    const browser = await chromium.launch({
        headless: false,
        args: ["--no-sandbox", "--disable-setuid-sandbox"],
    });

    const page = await browser.newPage();

    try {
        console.log("Navigating to http://localhost:8080");
        await page.goto("http://localhost:8080", { waitUntil: "networkidle" });
        await page.screenshot({ path: "diagnose-1-login.png" });

        console.log('Looking for "Create account" link...');
        const createAccountLink = await page.$('a:has-text("Create account"), button:has-text("Create account")');
        console.log("Create account link found:", !!createAccountLink);

        if (createAccountLink) {
            console.log('Clicking "Create account"...');
            await createAccountLink.click();
            await page.waitForTimeout(2000);
            await page.screenshot({ path: "diagnose-2-register.png" });

            console.log("Checking for form fields...");
            const username = await page.$('input[name="username"]');
            const email = await page.$('input[name="email"]');
            const password = await page.$('input[name="password"]');
            const confirm = await page.$('input[name="confirmPassword"]');

            console.log("Username field:", !!username);
            console.log("Email field:", !!email);
            console.log("Password field:", !!password);
            console.log("Confirm field:", !!confirm);

            // Get page HTML
            const html = await page.content();
            console.log("\nPage HTML snippet:");
            console.log(html.substring(0, 2000));

            // Check console errors
            page.on("console", (msg) => {
                console.log("Browser console:", msg.type(), msg.text());
            });
        }

        console.log("\nPress Ctrl+C to exit...");
        await new Promise(() => {}); // Keep browser open
    } catch (error) {
        console.error("Error:", error);
    } finally {
        await browser.close();
    }
}

diagnose();
