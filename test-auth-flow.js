const API_BASE = "http://localhost:8080/api/v1";

async function testAuthFlow() {
    try {
        console.log("=== Testing Auth Flow ===\n");

        // Step 1: Login
        console.log("1. Logging in...");
        const loginResponse = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                email: "admin@testrunner.com",
                password: "Admin123!",
            }),
        });

        if (!loginResponse.ok) {
            throw new Error(`Login failed: ${loginResponse.status} ${loginResponse.statusText}`);
        }

        const loginData = await loginResponse.json();

        console.log("   Login successful!");
        console.log("   Response keys:", Object.keys(loginData));
        console.log("   Has access_token:", !!loginData.access_token);
        console.log("   Has refresh_token:", !!loginData.refresh_token);
        console.log("   Has session_token:", !!loginData.session_token);
        console.log("   Has user:", !!loginData.user);

        if (loginData.user) {
            console.log("   User data:", JSON.stringify(loginData.user, null, 2));
        }

        const accessToken = loginData.access_token;
        console.log("\n   Access token (first 50 chars):", accessToken.substring(0, 50) + "...");

        // Decode JWT to see payload
        const tokenParts = accessToken.split(".");
        if (tokenParts.length === 3) {
            const payload = JSON.parse(Buffer.from(tokenParts[1], "base64").toString());
            console.log("\n   Token payload:", JSON.stringify(payload, null, 2));
        }

        // Step 2: Make authenticated request
        console.log("\n2. Testing authenticated request to /api/v1/schedules/...");
        const schedulesResponse = await fetch(`${API_BASE}/schedules/`, {
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        });

        if (!schedulesResponse.ok) {
            throw new Error(`Schedules request failed: ${schedulesResponse.status} ${schedulesResponse.statusText}`);
        }

        const schedules = await schedulesResponse.json();
        console.log("   Success! Schedules count:", Array.isArray(schedules) ? schedules.length : "not an array");
    } catch (error) {
        console.error("\n❌ Error:", error.message);
    }
}

testAuthFlow();
