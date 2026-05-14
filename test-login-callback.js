const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // 监控console日志
    page.on("console", (msg) => {
        console.log("🔍 Browser Console:", msg.text());
    });

    // 监控所有导航
    page.on("load", () => {
        console.log("🔄 Page loaded:", page.url());
    });

    // 监控hash变化
    page.on("framenavigated", () => {
        console.log("🔗 Hash changed:", page.url());
    });

    console.log("🎬 测试登录回调...\n");

    try {
        // 1. 打开登录页面
        console.log("📍 步骤 1: 打开登录页面...");
        await page.goto("http://localhost:8080/#login", { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(1000);
        console.log("✅ 初始URL:", page.url(), "\n");

        // 2. 填写登录信息
        console.log("📝 步骤 2: 填写登录信息...");
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.fill('input[type="password"]', "Demo1234");
        console.log("✅ 已填写: demotest@example.com / Demo1234\n");

        // 3. 点击登录按钮并监控变化
        console.log("🚀 步骤 3: 点击登录按钮并监控...");
        await page.click('button:has-text("Sign In")');
        console.log("✅ 按钮已点击\n");

        // 4. 等待并检查URL变化
        console.log("⏳ 步骤 4: 监控URL变化 (10秒)...");
        let urlChanged = false;
        let finalUrl = page.url();

        for (let i = 1; i <= 10; i++) {
            await page.waitForTimeout(1000);

            const currentUrl = page.url();
            if (currentUrl !== finalUrl) {
                console.log(`  [${i}s] URL已改变: ${finalUrl} → ${currentUrl}`);
                finalUrl = currentUrl;
                urlChanged = true;
            }

            if (currentUrl.includes("#dashboard")) {
                console.log(`\n✅ [${i}s] 成功跳转到 dashboard\n`);
                break;
            }

            // 检查错误
            const errorElement = await page.locator(".error-message").first();
            const hasError = (await errorElement.count()) > 0;

            if (hasError) {
                const errorText = await errorElement.textContent();
                console.log(`\n❌ [${i}s] 错误: ${errorText}\n`);
                break;
            }
        }

        // 5. 检查最终状态
        console.log("📊 最终状态:");
        console.log("  - URL:", finalUrl);
        console.log("  - URL是否改变:", urlChanged ? "✅ 是" : "❌ 否");

        const storage = await page.evaluate(() => ({
            access_token: localStorage.getItem("access_token") ? "存在" : "不存在",
            refresh_token: localStorage.getItem("refresh_token") ? "存在" : "不存在",
            session_token: localStorage.getItem("session_token") ? "存在" : "不存在",
            user: localStorage.getItem("user") ? "存在" : "不存在",
        }));

        console.log("  - localStorage:", storage);
        console.log("");

        // 6. 手动检查DOM状态
        const hasLoginForm = (await page.locator('input[type="email"]').count()) > 0;
        const hasDashboard = (await page.locator("h1, h2").count()) > 0;

        console.log("🔍 DOM状态:");
        console.log("  - 登录表单:", hasLoginForm ? "存在" : "不存在");
        console.log("  - Dashboard内容:", hasDashboard ? "存在" : "不存在");
        console.log("");

        // 7. 截图
        await page.screenshot({ path: ".context/test-callback-final.png" });
        console.log("📸 截图: .context/test-callback-final.png\n");

        console.log("⏸️  保持浏览器打开10秒...");
        await page.waitForTimeout(10000);
    } catch (error) {
        console.error("❌ 错误:", error.message);
        await page.screenshot({ path: ".context/test-callback-error.png" });
    } finally {
        await browser.close();
    }
})();
