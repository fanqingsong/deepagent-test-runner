/** Page is pre-opened via shortest.config baseUrl + SHORTEST_START_HASH — no navigation. */
const SNAPSHOT_FIRST =
  "Call browser_snapshot first. Do not navigate or click the sidebar — the target page is already loaded.";

/** Page content may load asynchronously; wait briefly then snapshot. */
const SNAPSHOT_AFTER_WAIT =
  "The page may be loading asynchronously. Call browser_snapshot. If the main content is still loading, wait 2 seconds and call browser_snapshot again.";

/** Assert exact visible strings appear in the accessibility snapshot. */
export function assertPage(...texts: string[]): string {
  return `${SNAPSHOT_FIRST} Pass if the snapshot contains all of: ${texts.map((t) => `"${t}"`).join(", ")}.`;
}

/** Pass when any one indicator is present (loading/empty states). */
export function assertPageAny(...texts: string[]): string {
  return `${SNAPSHOT_FIRST} Pass if the snapshot contains at least one of: ${texts.map((t) => `"${t}"`).join(", ")}.`;
}

/** After explicit navigate tool usage (navigation.test.ts only). */
export function assertAfterNavigate(...texts: string[]): string {
  return `Call browser_snapshot. Pass if the snapshot contains: ${texts.map((t) => `"${t}"`).join(", ")}.`;
}

export function assertAfterNavigateAny(...texts: string[]): string {
  return `Call browser_snapshot. Pass if the snapshot contains at least one of: ${texts.map((t) => `"${t}"`).join(", ")}.`;
}

/** Assert page after waiting for async content to load. */
export function assertPageLoaded(...texts: string[]): string {
  return `${SNAPSHOT_AFTER_WAIT} Pass if the snapshot contains all of: ${texts.map((t) => `"${t}"`).join(", ")}.`;
}

/** Interactive step: snapshot → action → snapshot → assert. */

/** Assert a validation/error message string in snapshot. */
export function assertError(message: string): string {
  return `${SNAPSHOT_AFTER_WAIT} Pass if the snapshot contains "${message}".`;
}

export function actThenAssert(action: string, expectation: string): string {
  return `Call browser_snapshot. ${action} Call browser_snapshot again. Pass if ${expectation}.`;
}
