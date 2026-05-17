import { test, expect } from "@playwright/test";

test.describe("百度 AI 新闻搜索", () => {
    test("搜索 AI 新闻并获取前十条", async ({ page }) => {
        // 1. 访问百度网站
        await page.goto("https://www.baidu.com", { waitUntil: "domcontentloaded" });

        // 等待页面完全加载并处理可能的弹窗
        await page.waitForTimeout(2000);

        // 尝试关闭可能的cookie同意弹窗
        try {
            const closeButton = page.locator('.close-btn, .c-icon-close, [aria-label="Close"]').first();
            if (await closeButton.isVisible({ timeout: 1000 }).catch(() => false)) {
                await closeButton.click();
                await page.waitForTimeout(500);
            }
        } catch (e) {
            // 没有弹窗，继续
        }

        // 2. 找到搜索框并输入 "AI新闻"
        // 使用JavaScript直接操作DOM，绕过可见性检查
        await page.evaluate(() => {
            const searchInput = document.getElementById("kw") as HTMLInputElement;
            if (searchInput) {
                searchInput.value = "AI新闻";
                searchInput.dispatchEvent(new Event("input", { bubbles: true }));
                searchInput.dispatchEvent(new Event("change", { bubbles: true }));
            }
        });

        await page.waitForTimeout(1000); // 等待搜索建议

        // 3. 点击搜索按钮
        // 也使用JavaScript点击
        await page.evaluate(() => {
            const searchButton = document.getElementById("su") as HTMLElement;
            if (searchButton) {
                searchButton.click();
            }
        });

        // 4. 等待搜索结果加载
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(2000); // 额外等待动态内容

        // 5. 截图保存搜索结果
        await page.screenshot({
            path: "baidu-ai-news-search.png",
            fullPage: true,
        });

        // 6. 获取前十条搜索结果
        // 使用更通用的选择器，不依赖特定CSS类
        const searchResults = await page.locator('div[id*="content_"], .c-container, div[class*="result"]').all();
        const count = searchResults.length;

        console.log(`========================================`);
        console.log(`百度 "AI新闻" 搜索结果 - 前十条`);
        console.log(`========================================`);
        console.log(`总共找到 ${count} 条结果\n`);

        const results = [];

        // 获取前十条（或实际数量，取较小值）
        const maxResults = Math.min(10, count);

        for (let i = 0; i < maxResults; i++) {
            try {
                const result = searchResults[i];

                // 使用JavaScript提取所有可见文本和链接
                const resultData = await result.evaluate((el: HTMLElement) => {
                    // 查找标题和链接
                    const titleLink = el.querySelector("a[href]");
                    const title = titleLink?.textContent?.trim() || el.querySelector("h1, h2, h3, h4")?.textContent?.trim() || "无标题";
                    const link = titleLink?.getAttribute("href") || "无链接";

                    // 获取整个结果块的文本内容作为摘要
                    const textContent = el.textContent?.trim() || "";
                    const summary = textContent.substring(0, 200);

                    // 尝试提取来源信息（通常在结果底部）
                    const sourceEl = el.querySelector('.c-color-gray, .c-gray, span[class*="source"], span[class*="time"]');
                    const source = sourceEl?.textContent?.trim() || "未知来源";

                    return { title, link, summary, source };
                });

                results.push({
                    index: i + 1,
                    ...resultData,
                });

                console.log(`${i + 1}. ${resultData.title}`);
                console.log(`   链接: ${resultData.link}`);
                console.log(`   来源: ${resultData.source}`);
                console.log(`   摘要: ${resultData.summary.substring(0, 100)}...`);
                console.log(``);
            } catch (error) {
                console.log(`${i + 1}. [解析错误] ${(error as Error).message}`);
            }
        }

        console.log(`========================================`);
        console.log(`搜索完成！共获取 ${maxResults} 条结果`);
        console.log(`截图已保存: baidu-ai-news-search.png`);
        console.log(`========================================`);

        // 7. 保存结果到 JSON 文件
        const fs = require("fs");
        fs.writeFileSync("baidu-ai-news-results.json", JSON.stringify(results, null, 2), "utf-8");
        console.log(`结果已保存到: baidu-ai-news-results.json`);

        // 8. 验证至少找到一些结果
        expect(count).toBeGreaterThan(0);
        expect(results.length).toBeGreaterThan(0);
    });
});
