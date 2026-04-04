"""Tests for the GitHub API client (mocked httpx)."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from feed.github import fetch_issues, check_org_membership, add_label, RateLimitError, RawIssue


SAMPLE_ISSUE = {
    "id": 1001,
    "number": 41,
    "title": "Use virtual threads",
    "body": "Prefer Executors.newVirtualThreadPerTaskExecutor() for I/O-bound work.",
    "user": {"login": "alice", "avatar_url": "https://avatars.githubusercontent.com/u/1"},
    "labels": [{"name": "memory"}, {"name": "java"}],
    "created_at": "2026-04-03T08:14:00Z",
}


def _mock_response(status_code: int, json_data=None, headers=None):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data or []
    response.headers = headers or {}
    response.raise_for_status = MagicMock()
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=response
        )
    return response


@pytest.mark.asyncio
async def test_fetch_issues_parses_response():
    mock_resp = _mock_response(200, [SAMPLE_ISSUE])

    with patch("feed.github.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        issues = await fetch_issues("org/repo", "2026-04-01T00:00:00Z", "token123")

    assert len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, RawIssue)
    assert issue.id == 1001
    assert issue.number == 41
    assert issue.title == "Use virtual threads"
    assert issue.user.login == "alice"
    assert issue.labels[0].name == "memory"
    assert issue.created_at == "2026-04-03T08:14:00Z"


@pytest.mark.asyncio
async def test_fetch_issues_passes_correct_params():
    mock_resp = _mock_response(200, [])

    with patch("feed.github.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        await fetch_issues("org/repo", "2026-04-01T00:00:00Z", "mytoken")

    call_kwargs = mock_client.get.call_args
    params = call_kwargs.kwargs.get("params", {}) or call_kwargs[1].get("params", {})
    assert params["since"] == "2026-04-01T00:00:00Z"
    assert params["labels"] == "memory"
    assert params["state"] == "open"


@pytest.mark.asyncio
async def test_check_org_membership_true_on_204():
    mock_resp = _mock_response(204)

    with patch("feed.github.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        result = await check_org_membership("myorg", "alice", "token")

    assert result is True


@pytest.mark.asyncio
async def test_check_org_membership_false_on_404():
    mock_resp = _mock_response(404)

    with patch("feed.github.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        result = await check_org_membership("myorg", "outsider", "token")

    assert result is False


@pytest.mark.asyncio
async def test_rate_limit_raises_on_fetch():
    mock_resp = _mock_response(403, headers={"X-RateLimit-Remaining": "0"})

    with patch("feed.github.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_resp

        with pytest.raises(RateLimitError):
            await fetch_issues("org/repo", "2026-04-01T00:00:00Z", "token")


@pytest.mark.asyncio
async def test_add_label_sends_correct_request():
    mock_resp = _mock_response(200, [{"name": "incorporated"}])

    with patch("feed.github.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        await add_label("org/repo", 41, "incorporated", "token")

    call_kwargs = mock_client.post.call_args
    url = call_kwargs.args[0] if call_kwargs.args else call_kwargs[0][0]
    assert "/repos/org/repo/issues/41/labels" in url
    json_body = call_kwargs.kwargs.get("json", {})
    assert "incorporated" in json_body["labels"]
