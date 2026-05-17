const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const SCREENSHOT_DIR = ".context/ui-test-screenshots";
const BUDGET = 35;
let steps = 0;

function step() {
    steps++;
    if (steps > BUDGET) {
        throw new Error(`Budget exceeded: ${steps}/${BUDGET}`);
    }
    console.log(`[STEP ${steps}/${BUDGET}]`);
    return steps;
}

function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

async function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

const tests = {
    "REG-001": { name: "Valid registration", status: "STEP_SKIP" },
    "REG-002": { name: "Duplicate email", status: "STEP_SKIP" },
    "REG-003": { name: "Email verification required", status: "STEP_SKIP" },
    "REG-004": { name: "Form validation - invalid email", status: "STEP_SKIP" },
    "ADV-002": { name: "Weak password", status: "STEP_SKIP" },
    "ADV-003": { name: "Password mismatch", status: "STEP_SKIP" },
    "VIS-002": { name: "Loading state", status: "STEP_SKIP" },
    "VIS-003": { name: "Success message", status: "STEP_SKIP" },
    "A11Y-001": { name: "Form labels", status: "STEP_SKIP" },
    "A11Y-003": { name: "Error announcements", status: "STEP_SKIP" },
};

async function runTests() {
    let pages = 0;
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();
    pages++;

    try {
        // REG-001: Valid registration
        console.log("\n=== REG-001: Valid registration ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await page.waitForLoadState("networkidle");
            await sleep(3000);

            step();
            const emailExists = await page.waitForSelector("#register-email", { timeout: 10000 });
            if (!emailExists) throw new Error("Email input not found");
            await page.fill("#register-email", "test@example.com");
            await page.fill("#register-password", "Test1234!");
            await page.fill("#register-confirm-password", "Test1234!");

            step();
            await page.click('button[type="submit"]');

            step();
            await page.waitForSelector('.success-message, .alert-success, [role="alert"]', { timeout: 5000 });
            const successMsg = await page.textContent('.success-message, .alert-success, [role="alert"]');

            if (successMsg && (successMsg.includes("success") || successMsg.includes("registered") || successMsg.includes("verification"))) {
                tests["REG-001"].status = "STEP_PASS";
                console.log("✓ REG-001 PASSED: Success message appeared");
            } else {
                tests["REG-001"].status = "STEP_FAIL";
                console.log("✗ REG-001 FAILED: Success message not found");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-001.png") });
            }
        } catch (e) {
            tests["REG-001"].status = "STEP_FAIL";
            console.log(`✗ REG-001 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-001.png") }).catch(() => {});
        }

        // REG-002: Duplicate email
        console.log("\n=== REG-002: Duplicate email ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await sleep(2000);

            step();
            await page.fill("#register-email", "test@example.com");
            await page.fill("#register-password", "Test1234!");
            await page.fill("#register-confirm-password", "Test1234!");

            step();
            await page.click('button[type="submit"]');

            step();
            await page.waitForSelector('.error-message, .alert-error, [role="alert"]', { timeout: 5000 });
            const errorMsg = await page.textContent('.error-message, .alert-error, [role="alert"]');

            if (errorMsg && (errorMsg.includes("already") || errorMsg.includes("exists"))) {
                tests["REG-002"].status = "STEP_PASS";
                console.log("✓ REG-002 PASSED: Duplicate email error appeared");
            } else {
                tests["REG-002"].status = "STEP_FAIL";
                console.log("✗ REG-002 FAILED: Duplicate error not found");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-002.png") });
            }
        } catch (e) {
            tests["REG-002"].status = "STEP_FAIL";
            console.log(`✗ REG-002 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-002.png") }).catch(() => {});
        }

        // REG-003: Email verification required
        console.log("\n=== REG-003: Email verification required ===");
        try {
            step();
            await page.goto("http://localhost:8080/#login");
            await sleep(2000);

            step();
            await page.fill("#login-email", "test@example.com");
            await page.fill("#login-password", "Test1234!");
            await page.click('button[type="submit"]');

            step();
            await page.waitForSelector('.error-message, .alert-error, [role="alert"]', { timeout: 5000 });
            const errorMsg = await page.textContent('.error-message, .alert-error, [role="alert"]');

            if (errorMsg && (errorMsg.includes("verify") || errorMsg.includes("email"))) {
                tests["REG-003"].status = "STEP_PASS";
                console.log("✓ REG-003 PASSED: Verification required error appeared");
            } else {
                tests["REG-003"].status = "STEP_FAIL";
                console.log("✗ REG-003 FAILED: Verification error not found");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-003.png") });
            }
        } catch (e) {
            tests["REG-003"].status = "STEP_FAIL";
            console.log(`✗ REG-003 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-003.png") }).catch(() => {});
        }

        // REG-004: Form validation - invalid email
        console.log("\n=== REG-004: Form validation - invalid email ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await sleep(2000);

            step();
            await page.fill("#register-email", "not-an-email");
            await page.fill("#register-password", "Test1234!");
            await page.fill("#register-confirm-password", "Test1234!");

            step();
            await page.click('button[type="submit"]');

            step();
            await sleep(1000);
            const hasError = await page.evaluate(() => {
                const emailInput = document.querySelector("#register-email");
                return (
                    emailInput &&
                    (emailInput.classList.contains("error") ||
                        emailInput.getAttribute("aria-invalid") === "true" ||
                        document.querySelector(".error-message") !== null)
                );
            });

            if (hasError) {
                tests["REG-004"].status = "STEP_PASS";
                console.log("✓ REG-004 PASSED: Invalid email validation appeared");
            } else {
                tests["REG-004"].status = "STEP_FAIL";
                console.log("✗ REG-004 FAILED: No validation error for invalid email");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-004.png") });
            }
        } catch (e) {
            tests["REG-004"].status = "STEP_FAIL";
            console.log(`✗ REG-004 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "REG-004.png") }).catch(() => {});
        }

        // ADV-002: Weak password
        console.log("\n=== ADV-002: Weak password ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await sleep(2000);

            step();
            await page.fill("#register-email", "test2@example.com");
            await page.fill("#register-password", "12345");
            await page.fill("#register-confirm-password", "12345");

            step();
            await page.click('button[type="submit"]');

            step();
            await sleep(1000);
            const hasError = await page.evaluate(() => {
                const pwdInput = document.querySelector("#register-password");
                const errorMsg = document.querySelector('.error-message, [role="alert"]');
                return (pwdInput && pwdInput.classList.contains("error")) || (errorMsg && errorMsg.textContent.includes("8 character"));
            });

            if (hasError) {
                tests["ADV-002"].status = "STEP_PASS";
                console.log("✓ ADV-002 PASSED: Weak password validation appeared");
            } else {
                tests["ADV-002"].status = "STEP_FAIL";
                console.log("✗ ADV-002 FAILED: No validation for weak password");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "ADV-002.png") });
            }
        } catch (e) {
            tests["ADV-002"].status = "STEP_FAIL";
            console.log(`✗ ADV-002 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "ADV-002.png") }).catch(() => {});
        }

        // ADV-003: Password mismatch
        console.log("\n=== ADV-003: Password mismatch ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await sleep(2000);

            step();
            await page.fill("#register-email", "test3@example.com");
            await page.fill("#register-password", "Test1234!");
            await page.fill("#register-confirm-password", "Different1!");

            step();
            await page.click('button[type="submit"]');

            step();
            await sleep(1000);
            const hasError = await page.evaluate(() => {
                const confirmInput = document.querySelector("#register-confirm-password");
                const errorMsg = document.querySelector('.error-message, [role="alert"]');
                return (confirmInput && confirmInput.classList.contains("error")) || (errorMsg && errorMsg.textContent.includes("match"));
            });

            if (hasError) {
                tests["ADV-003"].status = "STEP_PASS";
                console.log("✓ ADV-003 PASSED: Password mismatch validation appeared");
            } else {
                tests["ADV-003"].status = "STEP_FAIL";
                console.log("✗ ADV-003 FAILED: No validation for password mismatch");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "ADV-003.png") });
            }
        } catch (e) {
            tests["ADV-003"].status = "STEP_FAIL";
            console.log(`✗ ADV-003 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "ADV-003.png") }).catch(() => {});
        }

        // VIS-002: Loading state
        console.log("\n=== VIS-002: Loading state ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await sleep(2000);

            step();
            await page.fill("#register-email", "test4@example.com");
            await page.fill("#register-password", "Test1234!");
            await page.fill("#register-confirm-password", "Test1234!");

            step();
            const clickPromise = page.click('button[type="submit"]');
            await sleep(100);

            const isLoading = await page.evaluate(() => {
                const btn = document.querySelector('button[type="submit"]');
                return (
                    btn &&
                    (btn.disabled ||
                        btn.classList.contains("loading") ||
                        btn.getAttribute("aria-busy") === "true" ||
                        document.querySelector(".spinner, .loader") !== null)
                );
            });

            await clickPromise;

            if (isLoading) {
                tests["VIS-002"].status = "STEP_PASS";
                console.log("✓ VIS-002 PASSED: Loading state detected");
            } else {
                tests["VIS-002"].status = "STEP_FAIL";
                console.log("✗ VIS-002 FAILED: No loading state");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "VIS-002.png") });
            }
        } catch (e) {
            tests["VIS-002"].status = "STEP_FAIL";
            console.log(`✗ VIS-002 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "VIS-002.png") }).catch(() => {});
        }

        // VIS-003: Success message
        console.log("\n=== VIS-003: Success message ===");
        try {
            step();
            await page.waitForSelector('.success-message, .alert-success, [role="alert"]', { timeout: 5000 });
            const successBanner = await page.evaluate(() => {
                const el = document.querySelector('.success-message, .alert-success, [role="alert"]');
                if (!el) return null;
                const styles = window.getComputedStyle(el);
                return {
                    exists: true,
                    text: el.textContent,
                    bgColor: styles.backgroundColor,
                    color: styles.color,
                };
            });

            if (successBanner && successBanner.exists && successBanner.text) {
                const isGreen =
                    successBanner.bgColor.includes("0, 128, 0") ||
                    successBanner.bgColor.includes("76, 175, 80") ||
                    successBanner.bgColor.includes("green");
                tests["VIS-003"].status = isGreen ? "STEP_PASS" : "STEP_FAIL";
                console.log(`${isGreen ? "✓" : "✗"} VIS-003 ${isGreen ? "PASSED" : "FAILED"}: Success banner ${isGreen ? "is green" : "not green"}`);
            } else {
                tests["VIS-003"].status = "STEP_FAIL";
                console.log("✗ VIS-003 FAILED: No success banner");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "VIS-003.png") });
            }
        } catch (e) {
            tests["VIS-003"].status = "STEP_FAIL";
            console.log(`✗ VIS-003 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "VIS-003.png") }).catch(() => {});
        }

        // A11Y-001: Form labels
        console.log("\n=== A11Y-001: Form labels ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await sleep(500);

            step();
            const hasLabels = await page.evaluate(() => {
                const inputs = document.querySelectorAll("input[name]");
                let allHaveLabels = true;
                inputs.forEach((input) => {
                    const id = input.getAttribute("id");
                    const ariaLabel = input.getAttribute("aria-label");
                    const ariaLabelledby = input.getAttribute("aria-labelledby");
                    const label = id ? document.querySelector(`label[for="${id}"]`) : null;

                    if (!label && !ariaLabel && !ariaLabelledby) {
                        allHaveLabels = false;
                    }
                });
                return allHaveLabels;
            });

            if (hasLabels) {
                tests["A11Y-001"].status = "STEP_PASS";
                console.log("✓ A11Y-001 PASSED: All inputs have labels");
            } else {
                tests["A11Y-001"].status = "STEP_FAIL";
                console.log("✗ A11Y-001 FAILED: Missing form labels");
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "A11Y-001.png") });
            }
        } catch (e) {
            tests["A11Y-001"].status = "STEP_FAIL";
            console.log(`✗ A11Y-001 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "A11Y-001.png") }).catch(() => {});
        }

        // A11Y-003: Error announcements
        console.log("\n=== A11Y-003: Error announcements ===");
        try {
            step();
            await page.goto("http://localhost:8080/#register");
            await sleep(500);

            step();
            await page.fill("#register-email", "invalid-email");
            await page.click('button[type="submit"]');
            await sleep(1000);

            step();
            const errorHasAlert = await page.evaluate(() => {
                const errorEl = document.querySelector('.error-message, .alert-error, [role="alert"]');
                return errorEl && errorEl.getAttribute("role") === "alert";
            });

            if (errorHasAlert) {
                tests["A11Y-003"].status = "STEP_PASS";
                console.log('✓ A11Y-003 PASSED: Error has role="alert"');
            } else {
                tests["A11Y-003"].status = "STEP_FAIL";
                console.log('✗ A11Y-003 FAILED: Error missing role="alert"');
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, "A11Y-003.png") });
            }
        } catch (e) {
            tests["A11Y-003"].status = "STEP_FAIL";
            console.log(`✗ A11Y-003 FAILED: ${e.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, "A11Y-003.png") }).catch(() => {});
        }
    } catch (e) {
        if (e.message.includes("Budget exceeded")) {
            console.log("\n⚠️  BUDGET EXCEEDED - Marking remaining tests as skipped");
        } else {
            console.error(`\n❌ ERROR: ${e.message}`);
        }
    } finally {
        await browser.close();
    }

    // Report results
    console.log("\n" + "=".repeat(60));
    console.log("TEST RESULTS");
    console.log("=".repeat(60));

    const passed = Object.values(tests).filter((t) => t.status === "STEP_PASS").length;
    const failed = Object.values(tests).filter((t) => t.status === "STEP_FAIL").length;
    const skipped = Object.values(tests).filter((t) => t.status === "STEP_SKIP").length;

    Object.entries(tests).forEach(([id, test]) => {
        console.log(`${test.status.padEnd(12)} | ${id}: ${test.name}`);
    });

    console.log("=".repeat(60));
    console.log(`Tests: ${Object.keys(tests).length} | Passed: ${passed} | Failed: ${failed} | Skipped: ${skipped} | Pages visited: ${pages}`);
    console.log(`Steps used: ${steps}/${BUDGET}`);
    console.log("=".repeat(60));
}

ensureDir(SCREENSHOT_DIR);
runTests().catch(console.error);
