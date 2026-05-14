const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    console.log("🎬 开始验证登录功能...\n");

    try {
        // 1. 打开登录页面
        console.log("📍 步骤 1: 打开登录页面...");
        await page.goto("http://localhost:8080/#login", { waitUntil: "domcontentloaded", timeout: 10000 });
        await page.waitForTimeout(1000);
        console.log("✅ 页面已加载\n");

        // 2. 检查表单元素
        console.log("🔍 步骤 2: 检查表单元素...");
        const emailVisible = await page.locator('input[type="email"]').isVisible();
        const passVisible = await page.locator('input[type="password"]').isVisible();
        const buttonVisible = await page.locator('button:has-text("Sign In")').isVisible();

        console.log(`  邮箱输入框: ${emailVisible ? "✅" : "❌"}`);
        console.log(`  密码输入框: ${passVisible ? "✅" : "❌"}`);
        console.log(`  登录按钮: ${buttonVisible ? "✅" : "❌"}\n`);

        if (!emailVisible || !passVisible || !buttonVisible) {
            console.log("❌ 表单元素缺失，无法继续测试");
            await page.waitForTimeout(5000);
            return;
        }

        // 3. 填写登录信息
        console.log("📝 步骤 3: 填写登录信息...");
        await page.fill('input[type="email"]', "demotest@example.com");
        await page.fill('input[type="password"]', "Demo1234");
        console.log("✅ 已填写: demotest@example.com / Demo1234\n");

        // 4. 点击登录按钮
        console.log("🚀 步骤 4: 点击登录按钮...");
        await page.click('button:has-text("Sign In")');
        console.log("✅ 按钮已点击\n");

        // 5. 等待响应
        console.log("⏳ 步骤 5: 等待响应 (最多5秒)...");
        for (let i = 1; i <= 5; i++) {
            await page.waitForTimeout(1000);

            const url = page.url();

            // 检查错误消息
            const errorElement = await page.locator(".error-message").first();
            const hasError = (await errorElement.count()) > 0;

            if (hasError) {
                const errorText = await errorElement.textContent();
                console.log(`\n❌ 登录失败: ${errorText}\n`);
                break;
            }

            if (url.includes("#dashboard")) {
                console.log(`\n✅ 登录成功！已跳转到 dashboard\n`);

                // 检查 localStorage
                const storage = await page.evaluate(() => ({
                    access_token: localStorage.getItem("access_token") ? "存在" : "不存在",
                    refresh_token: localStorage.getItem("refresh_token") ? "存在" : "不存在",
                    session_token: localStorage.getItem("session_token") ? "存在" : "不存在",
                    user: localStorage.getItem("user") ? "存在" : "不存在",
                }));

                console.log("📦 localStorage 状态:");
                console.log(`  - access_token: ${storage.access_token}`);
                console.log(`  - refresh_token: ${storage.refresh_token}`);
                console.log(`  - session_token: ${storage.session_token}`);
                console.log(`  - user: ${storage.user}\n`);

                console.log("🎉 登录功能验证成功！\n");
                break;
            }

            if (i === 5) {
                console.log("\n⚠️  5秒后仍未跳转，可能登录失败\n");
            }
        }

        // 6. 截图并保持浏览器打开
        console.log("📸 截图保存到: .context/verify-login-final.png");
        await page.screenshot({ path: ".context/verify-login-final.png" });

        console.log("\n⏸️  浏览器将保持打开10秒供您查看...");
        await page.waitForTimeout(10000);
    } catch (error) {
        console.error("❌ 测试过程出错:", error.message);
        await page.screenshot({ path: ".context/verify-login-error.png" });
    } finally {
        await browser.close();
        console.log("\n✅ 测试完成");
    }
})();
