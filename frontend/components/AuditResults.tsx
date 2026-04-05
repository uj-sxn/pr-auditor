"use client";

type SecurityFlag = {
  severity: "high" | "medium" | "low";
  issue: string;
  file: string;
  evidence: string;
  fix: string;
};

type ArchitectResult = {
  grade: "A" | "B" | "C" | "D" | "F" | string;
  summary: string;
  structural_findings: string[];
  drupal_standards: string[];
  recommended_fixes: string[];
};

type SecurityResult = {
  status: "red" | "green" | string;
  summary: string;
  flags: SecurityFlag[];
  logic_risks: string[];
};

type ManagerResult = {
  summary: string;
  impact: string;
  risk_level: "low" | "medium" | "high" | string;
  release_readiness: string;
};

export type AuditPayload = {
  metadata: {
    pr_url: string;
    title: string;
    author: string;
    base_branch: string;
    head_branch: string;
    changed_files: Array<{
      filename: string;
      status: string;
      additions: number;
      deletions: number;
      changes: number;
    }>;
  };
  architect: ArchitectResult;
  security: SecurityResult;
  manager: ManagerResult;
  logs: string[];
};

type AuditResultsProps = {
  result: AuditPayload | null;
  isLoading: boolean;
};

const gradeStyle = (grade: string) => {
  if (grade === "A" || grade === "B") return "text-emerald-300";
  if (grade === "C") return "text-amber-300";
  return "text-rose-300";
};

const riskStyle = (status: string) => {
  return status?.toLowerCase() === "red"
    ? "bg-rose-500/20 border-rose-400 text-rose-200"
    : "bg-emerald-500/20 border-emerald-400 text-emerald-200";
};

export default function AuditResults({ result, isLoading }: AuditResultsProps) {
  if (isLoading) {
    return (
      <section className="rounded-2xl border border-cyan-500/30 bg-slate-900/70 p-5 shadow-[0_0_45px_rgba(8,145,178,0.15)] sm:p-6">
        <p className="text-cyan-200">Running multi-agent review...</p>
      </section>
    );
  }

  if (!result) {
    return (
      <section className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5 sm:p-6">
        <p className="text-slate-300">
          Submit a GitHub pull request URL to generate your architect grade, security flags, and stakeholder summary.
        </p>
      </section>
    );
  }

  return (
    <section className="grid gap-4">
      <article className="rounded-2xl border border-cyan-500/30 bg-slate-900/70 p-5 shadow-[0_0_55px_rgba(14,116,144,0.2)] sm:p-6">
        <p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Architect</p>
        <div className="mt-3 flex flex-wrap items-end gap-3 sm:gap-4">
          <p className={`text-4xl font-extrabold sm:text-5xl ${gradeStyle(result.architect.grade)}`}>
            {result.architect.grade}
          </p>
          <p className="pb-2 text-slate-200">Structural Integrity Grade</p>
        </div>
        <p className="mt-3 text-slate-300">{result.architect.summary}</p>
      </article>

      <article
        className={`rounded-2xl border p-5 shadow-[0_0_55px_rgba(15,23,42,0.3)] sm:p-6 ${riskStyle(result.security.status)}`}
      >
        <p className="text-xs uppercase tracking-[0.25em]">Security</p>
        <p className="mt-3 text-2xl font-bold uppercase">{result.security.status}</p>
        <p className="mt-2">{result.security.summary}</p>

        {result.security.flags.length > 0 ? (
          <div className="mt-4 space-y-3">
            {result.security.flags.map((flag, index) => (
              <div key={`${flag.issue}-${index}`} className="rounded-xl border border-white/20 bg-black/20 p-3">
                <p className="text-sm font-semibold uppercase">{flag.severity}: {flag.issue}</p>
                <p className="mt-1 break-words text-sm">File: {flag.file || "Unknown"}</p>
                <p className="mt-1 break-words text-sm">Evidence: {flag.evidence}</p>
                <p className="mt-1 break-words text-sm">Fix: {flag.fix}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm">No explicit high-confidence security flags were detected.</p>
        )}
      </article>

      <article className="rounded-2xl border border-amber-400/30 bg-slate-900/70 p-5 shadow-[0_0_45px_rgba(245,158,11,0.15)] sm:p-6">
        <p className="text-xs uppercase tracking-[0.25em] text-amber-300">Manager Summary</p>
        <p className="mt-3 text-slate-100">{result.manager.summary}</p>
        <p className="mt-3 text-slate-300">Impact: {result.manager.impact}</p>
        <p className="mt-2 text-slate-300">Risk Level: {result.manager.risk_level}</p>
        <p className="mt-2 text-slate-300">Release Readiness: {result.manager.release_readiness}</p>
      </article>
    </section>
  );
}
