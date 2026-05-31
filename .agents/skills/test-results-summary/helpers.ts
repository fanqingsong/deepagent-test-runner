// helpers.ts — deterministic utilities for test result formatting

/**
 * Convert milliseconds to a human-readable duration string.
 * Examples: 3500 → "3.5s", 120000 → "2m 0s", 750 → "750ms"
 */
export function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
    const minutes = Math.floor(ms / 60_000);
    const seconds = Math.round((ms % 60_000) / 1000);
    return `${minutes}m ${seconds}s`;
}

/**
 * Compute pass rate as a formatted percentage string.
 * Returns "100.0%" for perfect runs, "N/A" when total is 0.
 */
export function passRate(passed: number, total: number): string {
    if (total === 0) return "N/A";
    return `${((passed / total) * 100).toFixed(1)}%`;
}

/**
 * Classify a run status into a display category.
 */
export function statusEmoji(status: string): string {
    const map: Record<string, string> = {
        passed: "✅",
        failed: "❌",
        error: "⚠️",
        running: "⏳",
        pending: "⏳",
    };
    return map[status] ?? "❓";
}
