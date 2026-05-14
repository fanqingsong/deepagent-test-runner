import { test, expect } from "@playwright/test";

test("Test login endpoint", async ({ page }) => {
    // Navigate to app
    await page.goto("http://localhost:8080");
    await page.waitForLoadState("domcontentloaded");

    // Fill login form
    await page.fill('input[type="email"]', "admin@example.com");
    await page.fill('input[type="password"]', "admin123");

    // Submit
    await page.click('button:has-text("Sign In")');

    // Wait for response
    await page.waitForTimeout(3000);

    // Check result
    const url = page.url();
    console.log("Final URL:", url);

    // Check for error message
    const errorLocator = page.locator(".error-message");
    const hasError = await errorLocator.count();

    if (hasError > 0) {
        const errorText = await errorLocator.textContent();
        console.log("Error message:", errorText);
    } else {
        console.log("No error message found");
    }

    // Take screenshot
    await page.screenshot({ path: ".context/test-login-result.png" });
});
