const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    try {
        console.log("🎬 检查登录页面状态...\n");

        // Navigate to login page
        console.log("📍 打开登录页面...");
        await page.goto("http://localhost:8080/#login", { waitUntil: "domcontentloaded", timeout: 10000 });
        await page.waitForTimeout(2000);
        console.log("✅ 页面已加载\n");

        // Take initial screenshot
        await page.screenshot({ path: ".context/check-login-01-initial.png" });
        console.log("📸 截图已保存: .context/check-login-01-initial.png\n");

        // Check if form elements exist
        console.log("🔍 检查表单元素:");
        const emailExists = (await page.locator('input[type="email"]').count()) > 0;
        const passExists = (await page.locator('input[type="password"]').count()) > 0;
        const buttonExists = (await page.locator('button:has-text("Sign In")').count()) > 0;

        console.log("  - 邮箱输入框:", emailExists ? "✅ 存在" : "❌ 不存在");
        console.log("  - 密码输入框:", passExists ? "✅ 存在" : "❌ 不存在");
        console.log("  - 登录按钮:", buttonExists ? "✅ 存在" : "❌ 不存在");
        console.log("");

        // Fill credentials
        if (emailExists && passExists) {
            console.log("📝 填写登录信息...");
            await page.fill('input[type="email"]', "demotest@example.com");
            await page.fill('input[type="password"]', "Demo1234");
            console.log("✅ 已填写: demotest@example.com / Demo1234\n");

            await page.screenshot({ path: ".context/check-login-02-filled.png" });
            console.log("📸 截图已保存: .context/check-login-02-filled.png\n");
        }

        // Click login button
        if (buttonExists) {
            console.log("🚀 点击登录按钮...");
            await page.click('button:has-text("Sign In")');
            console.log("✅ 按钮已点击\n");

            // Wait and monitor
            console.log("⏳ 等待响应 (10秒)...");
            for (let i = 1; i <= 10; i++) {
                await page.waitForTimeout(1000);

                const url = page.url();
                const errorElement = await page.locator(".error-message").first();
                const hasError = (await errorElement.count()) > 0;

                console.log(`  [${i}s] URL: ${url}`);

                if (hasError) {
                    const errorText = await errorElement.textContent();
                    console.log(`  [${i}s] ❌ 错误信息: ${errorText}`);
                    break;
                }

                if (url.includes("#dashboard")) {
                    console.log(`  [${i}s] ✅ 成功跳转到 dashboard`);
                    break;
                }
            }
            console.log("");

            // Check final state
            const finalUrl = page.url();
            const storage = await page.evaluate(() => ({
                access_token: localStorage.getItem("access_token"),
                refresh_token: localStorage.getItem("refresh_token"),
                session_token: localStorage.getItem("session_token"),
                user: localStorage.getItem("user"),
            }));

            console.log("📊 最终状态:");
            console.log("  - URL:", finalUrl);
            console.log("  - access_token:", storage.access_token ? "✅ 存在" : "❌ 不存在");
            console.log("  - refresh_token:", storage.refresh_token ? "✅ 存在" : "❌ 不存在");
            console.log("  - session_token:", storage.session_token ? "✅ 存在" : "❌ 不存在");
            console.log("  - user:", storage.user ? "✅ 存在" : "❌ 不存在");
            console.log("");

            // Final screenshot
            await page.screenshot({ path: ".context/check-login-03-final.png" });
            console.log("📸 截图已保存: .context/check-login-03-final.png\n");
        }

        console.log("⏸️  浏览器将保持打开15秒供您查看...");
        await page.waitForTimeout(15000);
    } catch (error) {
        console.error("❌ 错误:", error.message);
        await page.screenshot({ path: ".context/check-login-error.png" });
    } finally {
        await browser.close();
    }
})();
