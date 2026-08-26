import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "@/api/health";

export function HomePage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });

  return (
    <main className="page">
      <header className="hero">
        <p className="brand">Monetra</p>
        <h1>Personal finance platform</h1>
        <p className="lede">
          Foundation scaffold is ready. Application features will be added incrementally
          against SPECIFICATIONS.md.
        </p>
      </header>

      <section className="status" aria-live="polite">
        <h2>Backend status</h2>
        {healthQuery.isPending && <p>Checking health endpoint…</p>}
        {healthQuery.isError && (
          <p className="error">
            Backend health check failed. Start Docker Compose or the API server.
          </p>
        )}
        {healthQuery.isSuccess && (
          <p className="ok">API health: {healthQuery.data.status}</p>
        )}
      </section>
    </main>
  );
}
