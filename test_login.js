const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: './videos/',
      size: { width: 1280, height: 720 }
    }
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

    // 等待页面加载
    await page.waitForTimeout(2000);

    // 截图
    await page.screenshot({ path: 'login_page.png', timeout: 5000 }).catch(() => console.log('Screenshot failed, continuing...'));
    console.log('Login page screenshot saved');

    // 填写登录表单
    console.log('Filling login form...');
    await page.fill('input[type="email"]', 'admin@example.com');
    await page.fill('input[type="password"]', 'admin123');

    // 截图
    await page.screenshot({ path: 'login_filled.png', timeout: 5000 }).catch(() => console.log('Screenshot failed, continuing...'));
    console.log('Form filled, screenshot saved');

    // 点击登录按钮
    console.log('Clicking login button...');
    await page.click('button[type="submit"]');

    // 等待导航
    await page.waitForTimeout(3000);

    // 截图
    await page.screenshot({ path: 'after_login.png', timeout: 5000 }).catch(() => console.log('Screenshot failed, continuing...'));
    console.log('After login screenshot saved');

    // 获取当前URL
    console.log('Current URL:', page.url());

    // 检查页面内容
    const pageContent = await page.content();
    console.log('Page title:', await page.title());

    // 等待一段时间观察页面
    await page.waitForTimeout(5000);

    // 最终截图
    await page.screenshot({ path: 'final_page.png', timeout: 5000 }).catch(() => console.log('Screenshot failed, continuing...'));
    console.log('Final page screenshot saved');

  } catch (error) {
    console.error('Error during login:', error);
    await page.screenshot({ path: 'error_screenshot.png', timeout: 5000 }).catch(() => {});
  } finally {
    await browser.close();
  }
})();
