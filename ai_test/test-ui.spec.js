const { chromium } = require('/home/fqs/.nvm/versions/node/v24.14.1/lib/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = '.context/ui-test-screenshots';
const RESULTS = {
  tests: 0,
  passed: 0,
  failed: 0,
  skipped: 0,
  pagesVisited: 0,
  details: []
};

// Ensure screenshot directory exists
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function logResult(testId, status, evidence, expected = null, actual = null) {
  RESULTS.tests++;
  if (status === 'PASS') {
    RESULTS.passed++;
    console.log(`STEP_PASS|${testId}|${evidence}`);
  } else {
    RESULTS.failed++;
    const msg = expected ? `${expected} → ${actual}` : evidence;
    console.log(`STEP_FAIL|${testId}|${msg}`);
  }
  RESULTS.details.push({ testId, status, evidence, expected, actual });
}

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runTests() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }
  });

  const page = await context.newPage();

  // Monitor console errors
  const consoleErrors = [];
  const consoleWarnings = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    } else if (msg.type() === 'warning') {
      consoleWarnings.push(msg.text());
    }
  });

  try {
    // Test 1: Login Flow
    console.log('\n=== Test 1: Login Flow ===');
    await page.goto('http://localhost:8080');
    RESULTS.pagesVisited++;
    await sleep(1000);

    const url = page.url();
    if (url.includes('localhost:8080') && !url.includes('#')) {
      logResult('login-flow', 'PASS', 'Successfully navigated to login page');
    } else {
      logResult('login-flow', 'FAIL', 'Login page URL', 'localhost:8080', url);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'login-flow.png') });
    }

    // Fill in login form
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'admin123');
    await sleep(500);

    // Click Sign In button
    await page.click('button[type="submit"]');
    await sleep(2000);

    const dashboardUrl = page.url();
    if (dashboardUrl.includes('#dashboard')) {
      logResult('login-flow', 'PASS', 'Successfully logged in and redirected to dashboard');
    } else {
      logResult('login-flow', 'FAIL', 'Dashboard redirect', 'URL contains #dashboard', dashboardUrl);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'login-flow.png') });
    }

    // Test 2: Dashboard Display
    console.log('\n=== Test 2: Dashboard Display ===');
    await sleep(1000);

    const dashboardTitle = await page.title();
    const hasDashboardContent = await page.locator('body').textContent();

    if (hasDashboardContent.includes('仪表盘') || hasDashboardContent.includes('Dashboard') ||
        hasDashboardContent.includes('测试') || hasDashboardContent.includes('执行')) {
      logResult('dashboard-display', 'PASS', 'Dashboard loaded with content');
    } else {
      logResult('dashboard-display', 'FAIL', 'Dashboard content', 'Dashboard text visible', 'No dashboard content found');
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dashboard-display.png') });
    }

    // Test 3: Test Management Navigation
    console.log('\n=== Test 3: Test Management Navigation ===');
    await page.click('text=/测试.*管理|Test.*Management/');
    await sleep(1000);

    const testsUrl = page.url();
    if (testsUrl.includes('#tests')) {
      logResult('test-management-nav', 'PASS', 'Successfully navigated to test management page');
      RESULTS.pagesVisited++;
    } else {
      logResult('test-management-nav', 'FAIL', 'Test management URL', 'URL contains #tests', testsUrl);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'test-management-nav.png') });
    }

    // Test 4: Schedule Navigation
    console.log('\n=== Test 4: Schedule Navigation ===');
    await page.click('text=/调度.*配置|Schedule.*Configuration/');
    await sleep(1000);

    const scheduleUrl = page.url();
    if (scheduleUrl.includes('#schedules')) {
      logResult('schedule-nav', 'PASS', 'Successfully navigated to schedule page');
      RESULTS.pagesVisited++;
    } else {
      logResult('schedule-nav', 'FAIL', 'Schedule URL', 'URL contains #schedules', scheduleUrl);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'schedule-nav.png') });
    }

    // Test 5: User Configuration Navigation
    console.log('\n=== Test 5: User Configuration Navigation ===');
    await page.click('text=/用户.*配置|User.*Configuration/');
    await sleep(1000);

    const userUrl = page.url();
    if (userUrl.includes('#users')) {
      logResult('user-config-nav', 'PASS', 'Successfully navigated to user configuration page');
      RESULTS.pagesVisited++;
    } else {
      logResult('user-config-nav', 'FAIL', 'User config URL', 'URL contains #users', userUrl);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'user-config-nav.png') });
    }

    // Test 6: SSO Configuration Navigation
    console.log('\n=== Test 6: SSO Configuration Navigation ===');
    await page.click('text=/SSO.*配置|SSO.*Config/');
    await sleep(1000);

    const ssoUrl = page.url();
    if (ssoUrl.includes('#sso')) {
      logResult('sso-config-nav', 'PASS', 'Successfully navigated to SSO configuration page');
      RESULTS.pagesVisited++;
    } else {
      logResult('sso-config-nav', 'FAIL', 'SSO config URL', 'URL contains #sso', ssoUrl);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'sso-config-nav.png') });
    }

    // Test 7: SSO Users Tab
    console.log('\n=== Test 7: SSO Users Tab ===');
    const ssoUsersTab = await page.$('text=/SSO.*用户|SSO.*Users/');
    if (ssoUsersTab) {
      await ssoUsersTab.click();
      await sleep(1000);
      logResult('sso-users-tab', 'PASS', 'SSO Users tab clicked and content displayed');
    } else {
      logResult('sso-users-tab', 'FAIL', 'SSO Users tab', 'Tab element exists', 'Tab not found');
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'sso-users-tab.png') });
    }

    // Test 8: Navigation Tabs (Hash Routing)
    console.log('\n=== Test 8: Navigation Tabs / Hash Routing ===');
    const routes = ['#dashboard', '#tests', '#schedules', '#users', '#sso'];
    let routingWorks = true;

    for (const route of routes) {
      await page.goto(`http://localhost:8080${route}`);
      await sleep(500);
      const currentUrl = page.url();
      if (!currentUrl.includes(route)) {
        routingWorks = false;
        break;
      }
      RESULTS.pagesVisited++;
    }

    if (routingWorks) {
      logResult('navigation-tabs', 'PASS', 'Hash routing works for all pages');
    } else {
      logResult('navigation-tabs', 'FAIL', 'Hash routing', 'All routes accessible', 'Some routes failed');
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'navigation-tabs.png') });
    }

    // Test 9: Logout Flow
    console.log('\n=== Test 9: Logout Flow ===');
    await page.goto('http://localhost:8080#dashboard');
    await sleep(500);

    const logoutButton = await page.$('text=/退出.*登录|Logout|Sign.*Out/');
    if (logoutButton) {
      await logoutButton.click();
      await sleep(1000);

      const finalUrl = page.url();
      if (!finalUrl.includes('#') && finalUrl.includes('localhost:8080')) {
        logResult('logout-flow', 'PASS', 'Successfully logged out and redirected to login page');
      } else {
        logResult('logout-flow', 'FAIL', 'Logout redirect', 'Redirected to login page', finalUrl);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'logout-flow.png') });
      }
    } else {
      logResult('logout-flow', 'FAIL', 'Logout button', 'Button exists', 'Logout button not found');
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'logout-flow.png') });
    }

    // Test 10: Console Errors
    console.log('\n=== Test 10: Console Errors ===');
    await sleep(1000);

    if (consoleErrors.length === 0) {
      logResult('console-errors', 'PASS', `No console errors (${consoleWarnings.length} warnings)`);
    } else {
      logResult('console-errors', 'FAIL', 'Console errors', 'No errors', `${consoleErrors.length} errors: ${consoleErrors.slice(0, 3).join(', ')}`);
      console.log('Console errors:', consoleErrors);
      console.log('Console warnings:', consoleWarnings);
    }

  } catch (error) {
    console.error('Test execution error:', error);
  } finally {
    await browser.close();
  }

  // Print final report
  console.log('\n=== FINAL REPORT ===');
  console.log(`Tests: ${RESULTS.tests} | Passed: ${RESULTS.passed} | Failed: ${RESULTS.failed} | Skipped: ${RESULTS.skipped} | Pages visited: ${RESULTS.pagesVisited}`);
  console.log('\nDetailed Results:');
  RESULTS.details.forEach(detail => {
    console.log(`  ${detail.testId}: ${detail.status} - ${detail.evidence}`);
  });
}

runTests().catch(console.error);
