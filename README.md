# The Feed

The Feed is a local daemon that polls a GitHub repository for issues labeled `memory`, classifies each one through a risk-based governor module, and lets you incorporate approved decisions directly into your local `CLAUDE.md` files — making team knowledge immediately available to Claude Code without any sync step, pull request, or central gatekeeper. Inspired by the Murderbot Diaries: every developer is their own SecUnit, in full control of what enters their programming.

## Quick start

```bash
export FEED_GITHUB_TOKEN=ghp_...
export FEED_GITHUB_REPO=org/team-brain
export FEED_GITHUB_ORG=org
export FEED_KNOWLEDGE_ROOT=~/code/team-brain

uv run feed
# open http://localhost:2626
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `FEED_GITHUB_TOKEN` | yes | — | GitHub personal access token (needs `repo` and `read:org` scopes) |
| `FEED_GITHUB_REPO` | yes | — | Repo to poll for issues, e.g. `org/team-brain` |
| `FEED_GITHUB_ORG` | yes | — | GitHub organisation used for sender trust checks |
| `FEED_KNOWLEDGE_ROOT` | no | `~/team-brain` | Local directory where `CLAUDE.md` files live |
| `FEED_PORT` | no | `2626` | Port the UI is served on |
| `FEED_POLL_INTERVAL` | no | `900` | Seconds between GitHub polls (frontend polls every 30 s) |

## Governor risk levels

| Level | Trigger | Actions available |
|---|---|---|
| **clear** | Trusted org member, no suspicious content | Incorporate · Filter |
| **review** | External URLs, imperative language + code blocks | Incorporate · Filter · Quarantine |
| **threat** | Non-org sender, shell injection (`\| bash`), `rm -rf`, `<script>`, `curl`/`wget` to external URL | Filter · Quarantine only |

Threat packets cannot be incorporated — the button is removed from the UI.

## GitHub repo setup

1. Create a repository (e.g. `org/team-brain`).
2. Add a PR template (`.github/pull_request_template.md`) with a `## Team Brain` section for the decision summary.
3. When merging a significant decision, tag the PR or open an Issue with:
   - the `memory` label (required — this is what The Feed polls for)
   - a domain label: `java`, `python`, `golang`, `api`, `testing`, `observability`, or `general`
4. The Feed will pick it up on the next poll and present it in the UI for your review.

## Domain → file mapping

| Domain label | Target file (relative to `FEED_KNOWLEDGE_ROOT`) |
|---|---|
| `java` | `language-guidelines/java.md` |
| `python` | `language-guidelines/python.md` |
| `golang` | `language-guidelines/golang.md` |
| `api` | `general-guidelines/specs-and-plans.md` |
| `testing` | `general-guidelines/testing.md` |
| `observability` | `general-guidelines/observability.md` |
| `general` | `CLAUDE.md` |

On incorporate, a dated block is appended to the target file:

```markdown
---
<!-- feed:#41 · akim.k · 2026-04-03T08:14:00Z -->
Prefer Executors.newVirtualThreadPerTaskExecutor() for all I/O-bound work.
---
```

Claude Code picks this up immediately — no pull, no restart.
