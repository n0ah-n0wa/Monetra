/**
 * Returns a same-origin in-app path or the fallback.
 * Rejects protocol-relative URLs, absolute URLs, and external paths.
 */
export function safeInternalPath(path: string | undefined, fallback: string): string {
  if (!path) {
    return fallback;
  }
  if (!path.startsWith("/") || path.startsWith("//")) {
    return fallback;
  }
  if (path.includes("://")) {
    return fallback;
  }
  return path;
}
