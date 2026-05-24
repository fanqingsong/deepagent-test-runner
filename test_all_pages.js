const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });

  const page = await context.newPage();

  let networkErrors = [];
  let consoleErrors = [];

  // 监听控制台错误
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
      console.log('❌ Console Error:', msg.text());
    }
  });

  // 监听页面错误
  page.on('pageerror', error => {
    consoleErrors.push(error.message);
    console.log('❌ Page Error:', error.message);
  });

  // 监听网络请求错误
  page.on('response', response => {
    if (response.status() >= 400) {
      networkErrors.push({ url: response.url(), status: response.status() });
      console.log(`❌ Network Error: ${response.url()} - Status: ${response.status()}`);
    }
  });

  try {
    console.log('🔐 Logging in...');
    await page.goto('http://localhost:8085/#login', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForTimeout(3000);

    // 测试各个页面
    const pages = [
      { name: 'Dashboard', url: 'http://localhost:8085/#dashboard' },
      { name: 'Tests', url: 'http://localhost:8085/#tests' },
      { name: 'Schedules', url: 'http://localhost:8085/#schedules' }
    ];

    for (const pageInfo of pages) {
      console.log(`\n📄 Testing ${pageInfo.name} page...`);
      await page.goto(pageInfo.url, { waitUntil: 'domcontentloaded', timeout: 10000 });
      await page.waitForTimeout(3000);
      console.log(`✅ ${pageInfo.name} page loaded: ${page.url()}`);
    }

    console.log('\n📊 Test Summary:');
    console.log(`Network Errors: ${networkErrors.length}`);
    console.log(`Console Errors: ${consoleErrors.length}`);

    if (networkErrors.length === 0 && consoleErrors.length === 0) {
      console.log('\n✅ All pages working correctly!');
    } else {
      console.log('\n❌ Some errors detected:');
      if (networkErrors.length > 0) {
        console.log(`  - ${networkErrors.length} network errors`);
      }
      if (consoleErrors.length > 0) {
        console.log(`  - ${consoleErrors.length} console errors`);
      }
    }

  } catch (error) {
    console.error('❌ Error during test:', error.message);
  } finally {
    await browser.close();
  }
})();
