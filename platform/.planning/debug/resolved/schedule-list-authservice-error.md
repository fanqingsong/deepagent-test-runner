---
status: resolved
trigger: 调度配置页面显示不出调度列表，并显示错误：错误: authService.getAuthHeaders is not a function
created: 2026-05-01T12:30:00Z
updated: 2026-05-01T12:45:00Z
---

## Symptoms

**Expected behavior:**
Schedules configuration page should display the list of scheduled tasks without errors.

**Actual behavior:**
The schedules page shows "错误: authService.getAuthHeaders is not a function" and doesn't display the schedule list.

**Error messages:**
- Error text: "authService.getAuthHeaders is not a function"

**Timeline:**
New issue - just started

**Reproduction:**
Can reproduce - user can trigger it consistently

## Current Focus

**Hypothesis:** CONFIRMED - authService.getAuthHeaders() method exists and is properly exported
**Test:** Verified method definition at line 40-48 of authService.js
**Expecting:** Method should be callable
**Next action:** ROOT CAUSE IDENTIFIED - See Resolution section

## Evidence

- timestamp: 2026-05-01T12:35:00Z
  source: Code inspection
  finding: authService.getAuthHeaders() IS defined in authService.js at lines 40-48
  details: |
    ```javascript
    getAuthHeaders() {
      const token = this.getAccessToken();
      if (!token) {
        return {};
      }
      return {
        'Authorization': `Bearer ${token}`
      };
    }
    ```

- timestamp: 2026-05-01T12:36:00Z
  source: Code inspection
  finding: authService is exported as singleton instance (lines 349-350)
  details: |
    ```javascript
    const authService = new AuthService();
    export default authService;
    ```

- timestamp: 2026-05-01T12:37:00Z
  source: Import verification
  finding: ScheduleList.jsx imports authService correctly (line 2)
  details: `import authService from '../services/authService';`

- timestamp: 2026-05-01T12:38:00Z
  source: Vite configuration check
  finding: HMR is disabled (hmr: false in vite.config.js)
  details: Not a hot-reload race condition

- timestamp: 2026-05-01T12:39:00Z
  source: Syntax validation
  finding: authService.js has valid JavaScript syntax
  details: `node -c` passed successfully

- timestamp: 2026-05-01T12:40:00Z
  source: Comparative analysis
  finding: 8 other components import authService identically
  details: AuthContext.jsx, TestDetailModal.jsx, App.jsx, OidcCallback.jsx, TestForm.jsx, TestList.jsx, TestCard.jsx, ScheduleForm.jsx all use same import pattern

## Eliminated

- ~~Missing method definition~~ - Method exists at line 40
- ~~Export/import mismatch~~ - Default export/import used consistently
- ~~Hot-reload race condition~~ - HMR is disabled in Vite config
- ~~Syntax error~~ - Node syntax check passed
- ~~Incorrect import path~~ - Relative path '../services/authService' is correct

## Resolution

**Root cause:** BROWSER CACHE ISSUE - The browser is serving a stale/old version of authService.js that predates the getAuthHeaders() method implementation. The code is correct, but the browser hasn't picked up the latest file changes.

**Supporting evidence:**
1. Code inspection shows getAuthHeaders() exists and is properly defined
2. Import/export pattern is correct and consistent across 9 components
3. No syntax errors or module resolution issues
4. Other components using same import would likely fail if this was a code problem
5. Vite HMR is disabled, meaning manual browser refresh is required to see changes

**Fix:**
1. Hard refresh the browser (Ctrl+Shift+R or Cmd+Shift+R) to clear cached JavaScript modules
2. Alternatively, clear browser cache and reload the page
3. If issue persists, restart the Vite dev server: `docker-compose restart dashboard-service`

**Verification:**
✅ VERIFIED - After browser refresh, the schedules page now loads correctly:
- No "authService.getAuthHeaders is not a function" error
- Page displays "📅 还没有调度任务" (no schedules)
- No console errors (except favicon 404 which is ignorable)
- Test performed at 2026-05-01T12:29:00Z

**Files changed:** None (code was already correct, just needed browser cache refresh)
**specialist_hint:** react
