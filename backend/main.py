from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from github import Github, GithubException
from pydantic import BaseModel, Field

load_dotenv()

from agents import run_pr_audit

MAX_PATCH_CHARS = 90_000

app = FastAPI(
    title="Agentic PR Auditor API",
    description="Multi-agent code review API for GitHub pull requests.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    pr_url: str = Field(..., description="GitHub pull request URL")


def _parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    parsed = urlparse(pr_url)
    if parsed.netloc.lower() != "github.com":
        raise ValueError("Only github.com pull request URLs are supported.")

    match = re.match(r"^/([^/]+)/([^/]+)/pull/(\d+)", parsed.path)
    if not match:
        raise ValueError("URL must follow: https://github.com/<owner>/<repo>/pull/<number>")

    owner, repo, number = match.group(1), match.group(2), int(match.group(3))
    return owner, repo, number


def _trim_diff(diff: str, max_chars: int = MAX_PATCH_CHARS) -> str:
    if len(diff) <= max_chars:
        return diff
    return (
        diff[:max_chars]
        + "\n\n[Diff truncated for model context size. Review full PR in GitHub for complete coverage.]"
    )


def _fetch_pr_context(pr_url: str) -> Dict[str, Any]:
    owner, repo_name, pull_number = _parse_pr_url(pr_url)

    github_token = os.getenv("GITHUB_TOKEN", "").strip() or None
    gh = Github(github_token) if github_token else Github()

    try:
        repo = gh.get_repo(f"{owner}/{repo_name}")
        pull = repo.get_pull(pull_number)
    except GithubException as exc:
        detail = f"Unable to fetch pull request: {exc.data.get('message', str(exc))}"
        raise ValueError(detail) from exc

    file_chunks: List[str] = []
    changed_files: List[Dict[str, Any]] = []

    for changed_file in pull.get_files():
        patch = changed_file.patch or ""
        changed_files.append(
            {
                "filename": changed_file.filename,
                "status": changed_file.status,
                "additions": changed_file.additions,
                "deletions": changed_file.deletions,
                "changes": changed_file.changes,
            }
        )

        if not patch:
            continue

        file_chunks.append(
            "\n".join(
                [
                    f"### File: {changed_file.filename}",
                    f"Status: {changed_file.status}",
                    patch,
                ]
            )
        )

    combined_diff = _trim_diff("\n\n".join(file_chunks))

    return {
        "pr_url": pr_url,
        "title": pull.title,
        "author": pull.user.login if pull.user else "unknown",
        "body": pull.body or "",
        "base_branch": pull.base.ref,
        "head_branch": pull.head.ref,
        "changed_files": changed_files,
        "diff": combined_diff,
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_pr(payload: AnalyzeRequest) -> Dict[str, Any]:
    try:
        pr_context = await asyncio.to_thread(_fetch_pr_context, payload.pr_url)
        audit = await asyncio.to_thread(run_pr_audit, pr_context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}") from exc

    return {
        "metadata": {
            "pr_url": pr_context["pr_url"],
            "title": pr_context["title"],
            "author": pr_context["author"],
            "base_branch": pr_context["base_branch"],
            "head_branch": pr_context["head_branch"],
            "changed_files": pr_context["changed_files"],
        },
        **audit,
    }
