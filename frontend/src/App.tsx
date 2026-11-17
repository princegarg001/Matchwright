import { NavLink, Route, Routes } from "react-router-dom";
import { ModelStatus } from "./components/ModelStatus";
import { APP_NAME } from "./lib/brand";
import { MatchDetailPage } from "./pages/MatchDetailPage";
import { MatchPage } from "./pages/MatchPage";
import { RankPage } from "./pages/RankPage";

function Mark() {
  return (
    <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
      <rect width="32" height="32" rx="7" fill="var(--color-blueprint)" />
      <path d="M7 11h7M18 11h7M7 21h7" stroke="var(--color-paper)" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M14 11c3 0 1 10 4 10h7" stroke="var(--color-paper)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}

const nav = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-blueprint-soft text-blueprint" : "text-slate hover:text-ink"}`;

export default function App() {
  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-10 focus:rounded focus:bg-sheet focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="border-b border-rule bg-sheet">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-5 py-3">
          <NavLink to="/" className="flex items-center gap-2.5 text-lg font-semibold tracking-tight">
            <Mark />
            {APP_NAME}
          </NavLink>
          <nav aria-label="Main" className="flex gap-1">
            <NavLink to="/" end className={nav}>Match</NavLink>
            <NavLink to="/rank" className={nav}>Rank</NavLink>
          </nav>
          <div className="ml-auto"><ModelStatus /></div>
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-5 py-10 md:py-14">
        <Routes>
          <Route path="/" element={<MatchPage />} />
          <Route path="/rank" element={<RankPage />} />
          <Route path="/matches/:id" element={<MatchDetailPage />} />
          <Route path="*" element={<p className="text-slate">This page doesn't exist. <NavLink to="/" className="text-blueprint underline">Go to Match</NavLink>.</p>} />
        </Routes>
      </main>

      <footer className="border-t border-rule">
        <p className="mx-auto max-w-6xl px-5 py-4 text-sm text-slate">
          Decision support only. Scores help a recruiter review faster; a person makes every hiring decision.
        </p>
      </footer>
    </div>
  );
}
