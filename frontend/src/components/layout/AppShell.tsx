import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
      {sidebarOpen ? (
        <button
          type="button"
          className="app-shell__backdrop"
          aria-label="Close navigation menu"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}
      <div className="app-shell__main">
        <Header onMenuToggle={() => setSidebarOpen((open) => !open)} />
        <main className="app-shell__content" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
