"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import AuditResults, { AuditPayload } from "../components/AuditResults";
import AuditLegend from "../components/AuditLegend";

const API_BASE =
  ((globalThis as any).process?.env?.NEXT_PUBLIC_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

const isLikelyGitHubPrUrl = (value: string) => {
  return /^https?:\/\/github\.com\/[^/]+\/[^/]+\/pull\/\d+/.test(value.trim());
};

const parseLogLine = (line: string) => {
  const match = line.match(/^\[(.*?)\]\s*(.*)$/);
  if (!match) {
    return { timestamp: "", message: line };
  }

  return { timestamp: match[1], message: match[2] };
};

const logTone = (message: string) => {
  const msg = message.toLowerCase();
  if (msg.includes("failed") || msg.includes("fallback")) return "text-rose-300";
  if (msg.includes("started")) return "text-cyan-300";
  if (msg.includes("completed") || msg.includes("finished")) return "text-emerald-300";
  if (msg.includes("high") || msg.includes("red")) return "text-amber-300";
  return "text-emerald-300";
};

export default function HomePage() {
  const [prUrl, setPrUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AuditPayload | null>(null);
  const [visibleLogs, setVisibleLogs] = useState<string[]>([]);
  const currentYear = new Date().getFullYear();

  const totalFiles = useMemo(() => result?.metadata.changed_files.length ?? 0, [result]);

  useEffect(() => {
    if (!result?.logs?.length) {
      setVisibleLogs([]);
      return;
    }

    setVisibleLogs([]);
    let index = 0;
    const timer = setInterval(() => {
      setVisibleLogs((prev) => {
        if (index >= result.logs.length) return prev;
        const next = [...prev, result.logs[index]];
        index += 1;
        return next;
      });
    }, 220);

    return () => clearInterval(timer);
  }, [result]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!isLikelyGitHubPrUrl(prUrl)) {
      setError("Enter a valid GitHub pull request URL.");
      return;
    }

    setIsLoading(true);
    setError("");
    setResult(null);
    setVisibleLogs([]);

    try {
      const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pr_url: prUrl.trim() }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Analysis request failed.");
      }

      setResult(payload as AuditPayload);
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Unknown error.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#07111f] text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.2),transparent_35%),radial-gradient(circle_at_80%_20%,rgba(245,158,11,0.18),transparent_30%),radial-gradient(circle_at_50%_80%,rgba(251,191,36,0.12),transparent_35%)]" />
      <div className="relative mx-auto grid max-w-7xl gap-6 px-3 py-6 sm:px-4 sm:py-8 md:px-8 md:py-10">
        <header className="rounded-3xl border border-cyan-400/30 bg-slate-900/70 p-5 shadow-[0_0_70px_rgba(34,211,238,0.15)] backdrop-blur sm:p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-cyan-300">Scarlet Hacks 2026 // Corporate Innovation</p>
          <h1 className="heading-display mt-3 text-3xl leading-tight text-cyan-100 md:text-5xl">
            Agentic PR Auditor Mission Control
          </h1>
          <p className="mt-3 max-w-3xl text-slate-300">
            A transparent Multi-agent code governance tool.
          </p>

          <form onSubmit={onSubmit} className="mt-6 grid gap-3 md:grid-cols-[1fr_auto]">
            <input
              value={prUrl}
              onChange={(event) => setPrUrl(event.target.value)}
              placeholder="https://github.com/owner/repo/pull/123"
              className="h-12 w-full rounded-xl border border-cyan-500/40 bg-slate-950/80 px-4 text-sm text-slate-100 outline-none transition focus:border-cyan-300 focus:ring-2 focus:ring-cyan-400/30"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="h-12 rounded-xl border border-amber-300/40 bg-amber-300/10 px-5 text-sm font-semibold text-amber-100 transition hover:bg-amber-300/20 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Analyzing..." : "Launch Audit"}
            </button>
          </form>

          {error ? <p className="mt-3 text-sm text-rose-300">{error}</p> : null}

          {result ? (
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
              <span className="rounded-full border border-slate-600 px-3 py-1">Files: {totalFiles}</span>
              <span className="rounded-full border border-slate-600 px-3 py-1">Author: {result.metadata.author}</span>
              <span className="rounded-full border border-slate-600 px-3 py-1">
                Branches: {result.metadata.base_branch} ← {result.metadata.head_branch}
              </span>
            </div>
          ) : null}
        </header>

        <section className="grid gap-6 xl:grid-cols-[1.05fr_1fr]">
          <article className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4 shadow-[inset_0_0_25px_rgba(12,74,110,0.25)] sm:p-5">
            <p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Glass Box: Agent Thought-Stream</p>
            <p className="mt-2 text-xs text-slate-400">
              Live execution narrative from each agent in plain language.
            </p>
            <div className="mt-4 h-[320px] overflow-y-auto rounded-xl border border-slate-700 bg-[#030712] p-3 text-[11px] leading-6 sm:h-[460px] sm:p-4 sm:text-xs">
              {visibleLogs.length === 0 ? (
                <p className="text-slate-500">Awaiting agent telemetry...</p>
              ) : (
                visibleLogs.map((line, idx) => {
                  const parsed = parseLogLine(line);
                  return (
                    <div
                      key={`${line}-${idx}`}
                      className="mb-2 rounded-lg border border-slate-800/90 bg-slate-950/50 px-3 py-2 transition-opacity duration-200"
                    >
                      <p className="text-[10px] text-slate-400 sm:text-[11px]">{parsed.timestamp || "runtime"}</p>
                      <p className={`mt-1 break-words ${logTone(parsed.message)}`}>{parsed.message}</p>
                    </div>
                  );
                })
              )}
            </div>
          </article>

          <AuditResults result={result} isLoading={isLoading} />
        </section>

        <AuditLegend result={result} />
      </div>

      <footer className="relative border-t border-slate-700/80 bg-slate-950/70">
        <div className="mx-auto max-w-7xl px-3 py-5 text-center text-xs text-slate-300 sm:px-4 sm:py-6 md:px-8">
          <p>Developed by Urjita Saxena &amp; Akshat Behera</p>
          <p className="mt-1">Copyright © {currentYear}. All rights reserved.</p>
        </div>
      </footer>
    </main>
  );
}
