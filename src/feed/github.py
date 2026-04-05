"""GitHub API client — async httpx-based."""

import os
from typing import Any
import httpx
from pydantic import BaseModel

GITHUB_API = "https://api.github.com"


class RateLimitError(Exception):
    """Raised when the GitHub API rate limit is exhausted."""


class IssueUser(BaseModel):
    login: str
    avatar_url: str = ""


class IssueLabel(BaseModel):
    name: str


class RawIssue(BaseModel):
    id: int
    number: int
    title: str
    body: str | None = ""
    user: IssueUser
    labels: list[IssueLabel] = []
    created_at: str
    repo: str = ""  # "owner/repo", populated by fetch_org_issues


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _check_rate_limit(response: httpx.Response) -> None:
    if response.status_code == 403:
        remaining = response.headers.get("X-RateLimit-Remaining", "1")
        if remaining == "0":
            raise RateLimitError("GitHub API rate limit exhausted")


async def fetch_issues(repo: str, since: str, token: str) -> list[RawIssue]:
    """Fetch open issues labeled 'memory' created/updated since the cursor."""
    url = f"{GITHUB_API}/repos/{repo}/issues"
    params = {
        "state": "open",
        "since": since,
        "labels": "memory",
        "per_page": "100",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_headers(token), params=params)
        _check_rate_limit(response)
        response.raise_for_status()
        return [RawIssue(**item) for item in response.json()]


async def fetch_org_issues(org: str, since: str, token: str) -> list[RawIssue]:
    """Fetch open issues labeled 'memory' across all org repos updated since cursor.

    Uses the Search API (one call) instead of per-repo endpoint (N+1 calls).
    Rate limit: 30 authenticated search requests/min — fine for polling use.
    """
    url = f"{GITHUB_API}/search/issues"
    query = f"label:memory org:{org} state:open updated:>{since}"
    params = {"q": query, "per_page": "100"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_headers(token), params=params)
        _check_rate_limit(response)
        response.raise_for_status()
        items = response.json().get("items", [])
        issues = []
        for item in items:
            # Derive "owner/repo" from repository_url like
            # "https://api.github.com/repos/owner/repo"
            repo_url = item.get("repository_url", "")
            repo_name = "/".join(repo_url.split("/")[-2:]) if repo_url else ""
            issue = RawIssue(**{k: v for k, v in item.items() if k != "repository_url"})
            issue.repo = repo_name
            issues.append(issue)
        return issues


async def check_org_membership(org: str, username: str, token: str) -> bool:
    """Return True if username is a member of org."""
    url = f"{GITHUB_API}/orgs/{org}/members/{username}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=_headers(token))
        _check_rate_limit(response)
        if response.status_code == 204 or response.status_code == 200:
            return True
        if response.status_code == 404 or response.status_code == 302:
            return False
        return False


async def add_label(repo: str, issue_number: int, label: str, token: str) -> None:
    """Add a label to a GitHub issue."""
    url = f"{GITHUB_API}/repos/{repo}/issues/{issue_number}/labels"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=_headers(token),
            json={"labels": [label]},
        )
        _check_rate_limit(response)
        response.raise_for_status()
