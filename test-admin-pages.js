const { chromium } = require("playwright");

(async () => {
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();

    // Collect console errors
    const consoleErrors = [];
    page.on("console", (msg) => {
        if (msg.type() === "error") {
            consoleErrors.push({
                type: "console",
                text: msg.text(),
                location: msg.location(),
            });
        }
    });

    // Collect network errors
    const networkErrors = [];
    page.on("response", (response) => {
        if (response.status() >= 400) {
            networkErrors.push({
                url: response.url(),
                status: response.status(),
                statusText: response.statusText(),
            });
        }
    });

    try {
        console.log("=== 测试管理员页面 ===\n");

        // Step 1: Login
        console.log("1. 登录中...");
        await page.goto("http://localhost:8080/#login", { waitUntil: "domcontentloaded", timeout: 10000 });
        await page.waitForTimeout(1000);

        // Clear localStorage first
        await page.evaluate(() => localStorage.clear());
        await page.reload({ waitUntil: "domcontentloaded", timeout: 10000 });
        await page.waitForTimeout(1000);

        // Fill login form
        await page.locator('input[type="email"], input[name="email"]').fill("admin@testrunner.com");
        await page.locator('input[type="password"]').fill("Admin123!");
        await page.locator('button[type="submit"], .login-button').click();

        // Wait for navigation to dashboard
        await page.waitForTimeout(3000);
        console.log("   ✅ 登录成功");
        console.log("   当前URL:", page.url());

        // Step 2: Test Schedule page
        console.log("\n2. 测试调度配置页面...");
        consoleErrors.length = 0;
        networkErrors.length = 0;

        await page.goto("http://localhost:8080/#schedules", { waitUntil: "domcontentloaded", timeout: 10000 });
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(2000);

        // Check for errors
        const scheduleError = await page.locator('.error, .error-message, [role="alert"]').count();
        console.log("   错误元素数量:", scheduleError);
        if (scheduleError > 0) {
            const errorText = await page.locator('.error, .error-message, [role="alert"]').first().textContent();
            console.log("   ❌ 调度配置页面错误:", errorText);
        } else {
            console.log("   ✅ 调度配置页面正常");
        }

        // Check page content
        const pageContent = await page.content();
        const hasScheduleList = pageContent.includes("调度配置") || pageContent.includes("Schedule");
        const hasTable = pageContent.includes("<table") || pageContent.includes("Table") || pageContent.includes("tbody");
        console.log("   包含'调度配置':", hasScheduleList);
        console.log("   包含表格:", hasTable);

        // Check console errors
        console.log("   控制台错误数:", consoleErrors.length);
        consoleErrors.forEach((err, i) => {
            console.log(`     [${i + 1}] ${err.text}`);
        });

        // Check network errors
        console.log("   网络错误数:", networkErrors.length);
        networkErrors.forEach((err, i) => {
            console.log(`     [${i + 1}] ${err.status} ${err.url}`);
        });

        await page.screenshot({ path: "schedule-page.png" });

        // Step 3: Test Users page
        console.log("\n3. 测试用户配置页面...");
        consoleErrors.length = 0;
        networkErrors.length = 0;

        await page.goto("http://localhost:8080/#users");
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(2000);

        const userError = await page.locator('.error, .error-message, [role="alert"]').count();
        console.log("   错误元素数量:", userError);
        if (userError > 0) {
            const errorText = await page.locator('.error, .error-message, [role="alert"]').first().textContent();
            console.log("   ❌ 用户配置页面错误:", errorText);
        } else {
            console.log("   ✅ 用户配置页面正常");
        }

        const usersPageContent = await page.content();
        const hasUsersList = usersPageContent.includes("用户配置") || usersPageContent.includes("User");
        const hasUsersTable = usersPageContent.includes("<table") || usersPageContent.includes("Table");
        console.log("   包含'用户配置':", hasUsersList);
        console.log("   包含表格:", hasUsersTable);

        console.log("   控制台错误数:", consoleErrors.length);
        consoleErrors.forEach((err, i) => {
            console.log(`     [${i + 1}] ${err.text}`);
        });

        console.log("   网络错误数:", networkErrors.length);
        networkErrors.forEach((err, i) => {
            console.log(`     [${i + 1}] ${err.status} ${err.url}`);
        });

        await page.screenshot({ path: "users-page.png" });

        // Step 4: Test SSO page
        console.log("\n4. 测试SSO配置页面...");
        consoleErrors.length = 0;
        networkErrors.length = 0;

        await page.goto("http://localhost:8080/#sso");
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(2000);

        const ssoError = await page.locator('.error, .error-message, [role="alert"]').count();
        console.log("   错误元素数量:", ssoError);
        if (ssoError > 0) {
            const errorText = await page.locator('.error, .error-message, [role="alert"]').first().textContent();
            console.log("   ❌ SSO配置页面错误:", errorText);
        } else {
            console.log("   ✅ SSO配置页面正常");
        }

        const ssoPageContent = await page.content();
        const hasSSOConfig = ssoPageContent.includes("SSO配置") || ssoPageContent.includes("SSO") || ssoPageContent.includes("SAML");
        const hasForm = ssoPageContent.includes("<form") || ssoPageContent.includes("input") || ssoPageContent.includes("button");
        console.log("   包含'SSO':", hasSSOConfig);
        console.log("   包含表单:", hasForm);

        console.log("   控制台错误数:", consoleErrors.length);
        consoleErrors.forEach((err, i) => {
            console.log(`     [${i + 1}] ${err.text}`);
        });

        console.log("   网络错误数:", networkErrors.length);
        networkErrors.forEach((err, i) => {
            console.log(`     [${i + 1}] ${err.status} ${err.url}`);
        });

        await page.screenshot({ path: "sso-page.png" });

        console.log("\n=== 测试完成 ===");
        console.log("截图已保存: schedule-page.png, users-page.png, sso-page.png");
    } catch (error) {
        console.error("测试失败:", error.message);
        await page.screenshot({ path: "test-failed.png" });
    } finally {
        await browser.close();
    }
})();
