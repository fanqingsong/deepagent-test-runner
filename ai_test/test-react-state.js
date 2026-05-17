const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // 监控所有console消息
    page.on("console", (msg) => {
        console.log("🔍 Console:", msg.type(), "-", msg.text());
    });

    // 监控错误
    page.on("pageerror", (error) => {
        console.log("💥 Page Error:", error.message);
    });

    console.log("🎬 测试React状态更新...\n");

    try {
        // 1. 打开登录页面
        console.log("📍 步骤 1: 打开登录页面...");
        await page.goto("http://localhost:8080/#login", { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(2000);
        console.log("✅ 初始URL:", page.url(), "\n");

        // 2. 填写登录信息
        console.log("📝 步骤 2: 填写登录信息...");
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.fill('input[type="password"]', "Demo1234");
        console.log("✅ 已填写登录信息\n");

        // 3. 检查登录前的DOM
        console.log("🔍 步骤 3: 检查登录前的DOM...");
        const loginBefore = await page.locator('input[type="email"]').count();
        const dashboardBefore = await page.locator("text=仪表板").count();
        console.log(`  登录表单: ${loginBefore > 0 ? "存在" : "不存在"}`);
        console.log(`  Dashboard导航: ${dashboardBefore > 0 ? "存在" : "不存在"}\n`);

        // 4. 点击登录
        console.log("🚀 步骤 4: 点击登录按钮...");
        await page.click('button:has-text("Sign In")');
        console.log("✅ 按钮已点击\n");

        // 5. 等待并监控变化
        console.log("⏳ 步骤 5: 等待状态更新 (5秒)...");
        for (let i = 1; i <= 5; i++) {
            await page.waitForTimeout(1000);

            const currentUrl = page.url();
            console.log(`  [${i}s] 当前URL: ${currentUrl}`);

            // 检查DOM变化
            const loginAfter = await page.locator('input[type="email"]').count();
            const dashboardAfter = await page.locator("text=仪表板").count();
            const navAfter = await page.locator("nav").count();

            console.log(`  [${i}s] 登录表单: ${loginAfter > 0 ? "存在" : "不存在"}`);
            console.log(`  [${i}s] Dashboard导航: ${dashboardAfter > 0 ? "存在" : "不存在"}`);
            console.log(`  [${i}s] 导航栏: ${navAfter > 0 ? "存在" : "不存在"}`);

            // 检查是否显示错误
            const errorElement = await page.locator(".error-message").first();
            if ((await errorElement.count()) > 0) {
                const errorText = await errorElement.textContent();
                console.log(`\n❌ 错误: ${errorText}\n`);
                break;
            }

            // 如果URL改变且dashboard导航出现，认为成功
            if (currentUrl.includes("#dashboard") && dashboardAfter > 0 && navAfter > 0) {
                console.log(`\n✅ 登录成功！Dashboard已显示\n`);
                break;
            }

            console.log("");
        }

        // 6. 最终截图
        await page.screenshot({ path: ".context/test-react-state-final.png" });
        console.log("📸 截图: .context/test-react-state-final.png\n");

        console.log("⏸️  保持浏览器打开15秒供您查看...");
        await page.waitForTimeout(15000);
    } catch (error) {
        console.error("❌ 错误:", error.message);
        await page.screenshot({ path: ".context/test-react-state-error.png" });
    } finally {
        await browser.close();
    }
})();
