/**
 * ZAP Spider Scan Script
 *
 * This script performs a spider scan of the target application
 * using the OWASP ZAP API.
 */

const ZAP_API_URL = process.env.ZAP_API_URL || "http://localhost:8090";
const TARGET_URL = process.env.TARGET_URL || "http://localhost:8080";

async function spiderScan() {
    console.log(`🕷️  Starting ZAP spider scan for: ${TARGET_URL}`);

    try {
        // Start spider scan
        const response = await fetch(
            `${ZAP_API_URL}/JSON/spider/action/scan/` + `?url=${encodeURIComponent(TARGET_URL)}` + `&maxChildren=10` + `&recurse=true`,
        );

        const data = await response.json();
        const scanId = data.scan;

        console.log(`✅ Spider scan started with ID: ${scanId}`);

        // Poll for progress
        let progress = 0;
        while (progress < 100) {
            await new Promise((resolve) => setTimeout(resolve, 2000));

            const statusResponse = await fetch(`${ZAP_API_URL}/JSON/spider/view/status/?scanId=${scanId}`);
            const statusData = await statusResponse.json();
            progress = parseInt(statusData.status);

            console.log(`📊 Spider progress: ${progress}%`);
        }

        console.log("✅ Spider scan completed");

        // Get results
        const resultsResponse = await fetch(`${ZAP_API_URL}/JSON/spider/view/results/?scanId=${scanId}`);
        const results = await resultsResponse.json();

        console.log(`📋 Found ${results.results.length} URLs`);

        return {
            success: true,
            urlsFound: results.results.length,
            scanId: scanId,
        };
    } catch (error) {
        console.error("❌ Spider scan failed:", error);
        return {
            success: false,
            error: error.message,
        };
    }
}

// Run spider scan if called directly
if (require.main === module) {
    spiderScan()
        .then((result) => {
            console.log(JSON.stringify(result, null, 2));
            process.exit(result.success ? 0 : 1);
        })
        .catch((error) => {
            console.error("Fatal error:", error);
            process.exit(1);
        });
}

module.exports = { spiderScan };
