const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });

  const page = await context.newPage();

  // 监听控制台错误
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('Console Error:', msg.text());
    }
  });

  // 监听页面错误
  page.on('pageerror', error => {
    console.log('Page Error:', error.message);
  });

  // 监听网络请求错误
  page.on('response', response => {
    if (response.status() >= 400) {
      console.log(`Network Error: ${response.url()} - Status: ${response.status()}`);
    }
  });

  try {
    console.log('Navigating to login page...');
    await page.goto('http://localhost:8085/#login', { waitUntil: 'domcontentloaded', timeout: 10000 });

    // 填写登录表单
    console.log('Logging in...');
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');

    // 等待登录完成
    await page.waitForTimeout(3000);

    console.log('Navigating to schedules page...');
    await page.goto('http://localhost:8085/#schedules', { waitUntil: 'domcontentloaded', timeout: 10000 });

    // 等待页面加载
    await page.waitForTimeout(5000);

    console.log('Current URL:', page.url());
    console.log('Page title:', await page.title());

    // 获取页面内容
    const pageContent = await page.content();
    console.log('Page loaded successfully');

  } catch (error) {
    console.error('Error during test:', error);
  } finally {
    await browser.close();
  }
})();
