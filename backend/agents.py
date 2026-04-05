from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, TypedDict

import google.generativeai as genai
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-latest").strip()
_RESOLVED_MODEL_NAME = ""


class AuditState(TypedDict):
    pr_url: str
    pr_title: str
    pr_author: str
    diff: str
    logs: List[str]
    architect: Dict[str, Any]
    security: Dict[str, Any]
    manager: Dict[str, Any]


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())


def _log(logs: List[str], message: str) -> List[str]:
    logs.append(f"[{_utc_ts()}] {message}")
    return logs


def _compact_error(exc: Exception, max_len: int = 260) -> str:
    raw = " ".join(str(exc).split())
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 3] + "..."


def _is_retryable_model_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    retry_markers = [
        "429",
        "quota",
        "rate",
        "resource_exhausted",
        "404",
        "not found",
        "not supported",
    ]
    return any(marker in msg for marker in retry_markers)


def _candidate_models() -> List[str]:
    models = [
        _RESOLVED_MODEL_NAME,
        MODEL_NAME,
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
    ]
    deduped: List[str] = []
    for model_name in models:
        if not model_name:
            continue
        if model_name in deduped:
            continue
        deduped.append(model_name)
    return deduped


def _configure_gemini() -> None:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY in backend/.env before running analysis."
        )
    genai.configure(api_key=api_key)


def _resolve_model_name() -> str:
    preferred = [
        MODEL_NAME,
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
    ]

    try:
        available: set[str] = set()
        for model in genai.list_models():
            methods = getattr(model, "supported_generation_methods", []) or []
            if "generateContent" not in methods:
                continue
            full_name = getattr(model, "name", "")
            if not full_name:
                continue
            available.add(full_name)
            if full_name.startswith("models/"):
                available.add(full_name.split("/", 1)[1])

        for candidate in preferred:
            if candidate and candidate in available:
                return candidate

        flash_models = sorted(
            m
            for m in available
            if "flash" in m.lower()
            and not m.startswith("models/")
            and "preview" not in m.lower()
            and "tts" not in m.lower()
            and "image" not in m.lower()
        )
        if flash_models:
            return flash_models[0]
    except Exception:
        pass

    return MODEL_NAME or "gemini-1.5-flash-latest"


def _model() -> genai.GenerativeModel:
    global _RESOLVED_MODEL_NAME
    _configure_gemini()
    if not _RESOLVED_MODEL_NAME:
        _RESOLVED_MODEL_NAME = _resolve_model_name()
    return genai.GenerativeModel(_RESOLVED_MODEL_NAME)


def _extract_json(text: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    if not text:
        return fallback

    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        candidate = candidate.replace("json", "", 1).strip()

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return fallback

    try:
        parsed = json.loads(candidate[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
        return fallback
    except json.JSONDecodeError:
        return fallback


def _prompt_template(role: str, objective: str, output_contract: str) -> str:
    return (
        f"You are Agent {role} in a multi-agent PR review system. "
        "Use only the provided pull request context and diff. "
        "Do not invent files or behavior that are not in the diff. "
        f"Objective: {objective}\n"
        "Return only valid JSON. No markdown, no prose outside JSON.\n"
        f"JSON contract: {output_contract}"
    )


def _invoke_agent(
    system_prompt: str,
    pr_context: str,
    logs: List[str] | None = None,
    agent_label: str | None = None,
) -> str:
    global _RESOLVED_MODEL_NAME

    _configure_gemini()
    if not _RESOLVED_MODEL_NAME:
        _RESOLVED_MODEL_NAME = _resolve_model_name()

    candidates = _candidate_models()
    last_exc: Exception | None = None

    for idx, model_name in enumerate(candidates):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                [system_prompt, "\n\nPR context and diff:\n", pr_context],
                generation_config={"temperature": 0.2, "top_p": 0.9},
            )

            if model_name != _RESOLVED_MODEL_NAME:
                _RESOLVED_MODEL_NAME = model_name
                if logs is not None and agent_label is not None:
                    _log(logs, f"{agent_label} switched model to {_RESOLVED_MODEL_NAME}.")

            return (response.text or "").strip()
        except Exception as exc:
            last_exc = exc
            retryable = _is_retryable_model_error(exc)
            has_next = idx < len(candidates) - 1
            if logs is not None and agent_label is not None and retryable and has_next:
                _log(
                    logs,
                    f"{agent_label} model {model_name} unavailable ({_compact_error(exc, 120)}). Trying next model.",
                )
            if not retryable or not has_next:
                raise

    if last_exc is not None:
        raise last_exc
    raise RuntimeError("No candidate Gemini model available.")


def _architect_node(state: AuditState) -> Dict[str, Any]:
    logs = list(state["logs"])
    started = time.time()
    _log(logs, "Agent A (Architect) started: reviewing architecture, module boundaries, and Drupal-style standards.")

    prompt = _prompt_template(
        role="A (Architect)",
        objective=(
            "Assess architecture quality, structural integrity, modularity, maintainability, "
            "and alignment with Drupal-style coding standards and governance expectations."
        ),
        output_contract=(
            "{"
            '"grade":"A|B|C|D|F",'
            '"summary":"string",'
            '"structural_findings":["string"],'
            '"drupal_standards":["string"],'
            '"recommended_fixes":["string"]'
            "}"
        ),
    )

    default = {
        "grade": "C",
        "summary": "Architect analysis was inconclusive.",
        "structural_findings": ["The model response could not be parsed."],
        "drupal_standards": ["Could not verify Drupal-style compliance from output."],
        "recommended_fixes": ["Retry analysis and inspect changed modules manually."],
    }
    try:
        raw = _invoke_agent(prompt, state["diff"], logs, "Agent A (Architect)")
        architect = _extract_json(raw, default)
    except Exception as exc:
        architect = {
            **default,
            "summary": "Architect analysis is temporarily unavailable due to model provider limits.",
        }
        _log(logs, f"Agent A provider issue: {_compact_error(exc)}")
    grade = str(architect.get("grade", "C"))
    findings = architect.get("structural_findings", [])
    if isinstance(findings, list) and findings:
        _log(logs, f"Agent A highlight: {findings[0]}")
    _log(logs, f"Agent A (Architect) completed in {round(time.time() - started, 2)}s with grade {grade}.")
    return {"architect": architect, "logs": logs}


def _security_node(state: AuditState) -> Dict[str, Any]:
    logs = list(state["logs"])
    started = time.time()
    _log(logs, "Agent B (Security) started: scanning for secrets, injection, auth flaws, and risky logic.")

    prompt = _prompt_template(
        role="B (Security)",
        objective=(
            "Find leaked credentials, SQL injection vectors, auth bypasses, insecure deserialization, "
            "and high-risk logic flaws in the changed code."
        ),
        output_contract=(
            "{"
            '"status":"red|green",'
            '"summary":"string",'
            '"flags":[{"severity":"high|medium|low","issue":"string","file":"string","evidence":"string","fix":"string"}],'
            '"logic_risks":["string"]'
            "}"
        ),
    )

    default = {
        "status": "green",
        "summary": "Security analysis was inconclusive.",
        "flags": [],
        "logic_risks": ["The model response could not be parsed."],
    }
    try:
        raw = _invoke_agent(prompt, state["diff"], logs, "Agent B (Security)")
        security = _extract_json(raw, default)
    except Exception as exc:
        security = {
            "status": "red",
            "summary": "Security analysis is temporarily unavailable due to model provider limits.",
            "flags": [
                {
                    "severity": "medium",
                    "issue": "Security scan not executed",
                    "file": "n/a",
                    "evidence": _compact_error(exc),
                    "fix": "Retry analysis when quota is available.",
                }
            ],
            "logic_risks": ["Unknown until automated or manual review completes."],
        }
        _log(logs, f"Agent B provider issue: {_compact_error(exc)}")
    flags = security.get("flags", [])
    if not isinstance(flags, list):
        flags = []
    high_count = len([f for f in flags if isinstance(f, dict) and str(f.get("severity", "")).lower() == "high"])
    status = str(security.get("status", "green")).upper()
    if flags:
        first_flag = flags[0]
        if isinstance(first_flag, dict):
            issue = str(first_flag.get("issue", "Potential issue"))
            severity = str(first_flag.get("severity", "unknown")).upper()
            _log(logs, f"Agent B highlight: {severity} - {issue}.")
    _log(
        logs,
        f"Agent B (Security) completed in {round(time.time() - started, 2)}s with status {status}, {len(flags)} total flags, {high_count} high severity.",
    )
    return {"security": security, "logs": logs}


def _manager_node(state: AuditState) -> Dict[str, Any]:
    logs = list(state["logs"])
    started = time.time()
    _log(logs, "Agent C (Manager) started: translating technical findings into stakeholder impact and release guidance.")

    prompt = _prompt_template(
        role="C (Manager)",
        objective=(
            "Translate technical changes and risks into plain-English impact for non-technical stakeholders, "
            "including business value, delivery risk, and release readiness."
        ),
        output_contract=(
            "{"
            '"summary":"string",'
            '"impact":"string",'
            '"risk_level":"low|medium|high",'
            '"release_readiness":"string"'
            "}"
        ),
    )

    pr_context = (
        f"PR Title: {state['pr_title']}\n"
        f"PR Author: {state['pr_author']}\n"
        f"Architect findings: {json.dumps(state.get('architect', {}))}\n"
        f"Security findings: {json.dumps(state.get('security', {}))}\n\n"
        f"Code diff:\n{state['diff']}"
    )
    default = {
        "summary": "Manager summary is unavailable.",
        "impact": "Unable to estimate business impact from model output.",
        "risk_level": "medium",
        "release_readiness": "Needs manual review before release.",
    }
    try:
        raw = _invoke_agent(prompt, pr_context, logs, "Agent C (Manager)")
        manager = _extract_json(raw, default)
    except Exception as exc:
        manager = {
            "summary": "Manager summary is temporarily unavailable due to model provider limits.",
            "impact": "Business impact is unknown until model access recovers.",
            "risk_level": "high",
            "release_readiness": "Hold release pending successful automated or manual review.",
        }
        _log(logs, f"Agent C provider issue: {_compact_error(exc)}")
    risk = str(manager.get("risk_level", "medium"))
    readiness = str(manager.get("release_readiness", "Needs manual review."))
    _log(logs, f"Agent C summary: risk level {risk}; release guidance -> {readiness}")
    _log(logs, f"Agent C (Manager) completed in {round(time.time() - started, 2)}s.")
    return {"manager": manager, "logs": logs}


def _build_graph():
    workflow = StateGraph(AuditState)
    workflow.add_node("architect", _architect_node)
    workflow.add_node("security", _security_node)
    workflow.add_node("manager", _manager_node)

    workflow.set_entry_point("architect")
    workflow.add_edge("architect", "security")
    workflow.add_edge("security", "manager")
    workflow.add_edge("manager", END)

    return workflow.compile()


AUDIT_GRAPH = _build_graph()


def run_pr_audit(pr_context: Dict[str, Any]) -> Dict[str, Any]:
    logs: List[str] = []
    _log(logs, "Pipeline received PR context.")
    _configure_gemini()
    selected_model = _resolve_model_name()
    global _RESOLVED_MODEL_NAME
    _RESOLVED_MODEL_NAME = selected_model
    _log(logs, f"Model selected: {_RESOLVED_MODEL_NAME}")

    changed_files = pr_context.get("changed_files", [])
    changed_count = len(changed_files) if isinstance(changed_files, list) else 0
    diff_chars = len(pr_context.get("diff", ""))
    _log(logs, f"Mission brief: reviewing {changed_count} changed files and {diff_chars} diff characters.")

    initial: AuditState = {
        "pr_url": pr_context["pr_url"],
        "pr_title": pr_context["title"],
        "pr_author": pr_context["author"],
        "diff": pr_context["diff"],
        "logs": logs,
        "architect": {},
        "security": {},
        "manager": {},
    }

    started = time.time()
    try:
        final_state = AUDIT_GRAPH.invoke(initial)
        elapsed = round(time.time() - started, 2)

        final_logs = list(final_state.get("logs", []))
        _log(final_logs, f"Pipeline finished in {elapsed} seconds.")

        return {
            "architect": final_state.get("architect", {}),
            "security": final_state.get("security", {}),
            "manager": final_state.get("manager", {}),
            "logs": final_logs,
        }
    except Exception as exc:
        error_brief = _compact_error(exc)
        _log(logs, f"Pipeline failed: {error_brief}")
        _log(logs, "Returning fallback audit result due to provider or quota issue.")
        return {
            "architect": {
                "grade": "C",
                "summary": "Automated architect analysis is temporarily unavailable.",
                "structural_findings": ["LLM provider request failed."],
                "drupal_standards": ["Could not evaluate standards in this run."],
                "recommended_fixes": ["Retry shortly or use a key with available quota."],
            },
            "security": {
                "status": "red",
                "summary": "Automated security analysis is temporarily unavailable.",
                "flags": [
                    {
                        "severity": "medium",
                        "issue": "Security scan was not executed",
                        "file": "n/a",
                        "evidence": error_brief,
                        "fix": "Retry analysis when Gemini quota is available.",
                    }
                ],
                "logic_risks": ["Unknown until automated or manual review completes."],
            },
            "manager": {
                "summary": "Automated PM summary is temporarily unavailable.",
                "impact": "Business impact could not be generated in this run.",
                "risk_level": "high",
                "release_readiness": "Hold release pending successful automated or manual review.",
            },
            "logs": logs,
        }
