"use client";

import type { AuditPayload } from "./AuditResults";

type AuditLegendProps = {
  result: AuditPayload | null;
};

const gradeTone = (grade: string) => {
  if (grade === "A" || grade === "B") return "border-emerald-400/40 text-emerald-200";
  if (grade === "C") return "border-amber-400/40 text-amber-200";
  return "border-rose-400/40 text-rose-200";
};

const statusTone = (status: string) => {
  return status?.toLowerCase() === "red"
    ? "border-rose-400/40 text-rose-200"
    : "border-emerald-400/40 text-emerald-200";
};

const managerRiskTone = (risk: string) => {
  const value = (risk || "").toLowerCase();
  if (value === "low") return "border-emerald-400/40 text-emerald-200";
  if (value === "medium") return "border-amber-400/40 text-amber-200";
  return "border-rose-400/40 text-rose-200";
};

export default function AuditLegend({ result }: AuditLegendProps) {
  return (
    <section className="rounded-2xl border border-slate-700/80 bg-slate-950/70 p-5 shadow-[0_0_45px_rgba(15,23,42,0.35)] sm:p-6">
      <p className="text-xs uppercase tracking-[0.25em] text-cyan-300">Report Legend</p>
      <p className="mt-3 text-sm text-slate-300">
        This guide maps each metric to the correct agent and explains what each result means for merge readiness.
      </p>

      <div className="mt-4 grid gap-3 lg:grid-cols-3">
        <div className="rounded-xl border border-cyan-500/30 bg-slate-900/70 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-cyan-300">Agent A - Architect</p>
          <p className="mt-2 text-sm text-slate-200">
            Outputs: grade, summary, structural findings, Drupal standards, recommended fixes.
          </p>
          <p className="mt-2 text-sm text-slate-300">Grade scale:</p>
          <p className="mt-1 text-xs text-emerald-300">A-B: Strong structure and maintainability.</p>
          <p className="mt-1 text-xs text-amber-300">C: Acceptable, but needs improvement.</p>
          <p className="mt-1 text-xs text-rose-300">D-F: High architecture risk or weak standards alignment.</p>
        </div>

        <div className="rounded-xl border border-rose-500/30 bg-slate-900/70 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-rose-300">Agent B - Security</p>
          <p className="mt-2 text-sm text-slate-200">Outputs: status, flags, logic risks, evidence, suggested fixes.</p>
          <p className="mt-2 text-xs text-slate-300">Status:</p>
          <p className="mt-1 text-xs text-rose-300">Red: one or more concerning security risks were detected.</p>
          <p className="mt-1 text-xs text-emerald-300">Green: no high-confidence risks found in changed code.</p>
          <p className="mt-2 text-xs text-slate-300">
            Severity scale: High = urgent exploit risk, Medium = important before merge, Low = hygiene hardening.
          </p>
        </div>

        <div className="rounded-xl border border-amber-500/30 bg-slate-900/70 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-amber-300">Agent C - Manager</p>
          <p className="mt-2 text-sm text-slate-200">
            Outputs: plain-English summary, business impact, risk level, and release readiness.
          </p>
          <p className="mt-2 text-xs text-slate-300">Risk/impact interpretation:</p>
          <p className="mt-1 text-xs text-emerald-300">Low: safe to proceed with routine caution.</p>
          <p className="mt-1 text-xs text-amber-300">Medium: proceed with targeted mitigations.</p>
          <p className="mt-1 text-xs text-rose-300">High: hold release until critical concerns are resolved.</p>
        </div>
      </div>

      {result ? (
        <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900/60 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-300">Current Assessment Snapshot</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className={`rounded-full border px-3 py-1 ${gradeTone(result.architect.grade)}`}>
              Architect Grade: {result.architect.grade}
            </span>
            <span className={`rounded-full border px-3 py-1 ${statusTone(result.security.status)}`}>
              Security Status: {result.security.status.toUpperCase()}
            </span>
            <span className={`rounded-full border px-3 py-1 ${managerRiskTone(result.manager.risk_level)}`}>
              Manager Risk: {result.manager.risk_level}
            </span>
            <span className="rounded-full border border-slate-600 px-3 py-1 text-slate-300">
              Security Flags: {result.security.flags.length}
            </span>
          </div>
        </div>
      ) : null}
    </section>
  );
}
