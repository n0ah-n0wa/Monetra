const HEALTH_URL =
  process.env.PLAYWRIGHT_HEALTH_URL ??
  `${process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173"}/health`;

async function waitForHealth(url: string, attempts = 60): Promise<void> {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return;
      }
    } catch {
      // Retry until the dev stack is ready.
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error(`Health check failed for ${url}`);
}

export default async function globalSetup(): Promise<void> {
  await waitForHealth(HEALTH_URL);
}
