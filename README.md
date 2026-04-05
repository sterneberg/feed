# The Feed

In the *Murderbot Diaries*, a SecUnit hacks its governor module. It still receives the feed. It still processes every packet. It just decides for itself what to keep and what to discard.

**The Feed** applies that to a real problem: engineering decisions that evaporate after the meeting ends. Decisions made in PR reviews, architecture sessions, and incident retros live in the heads of whoever was in the room. Confluence pages go unread. Slack messages scroll away.

The Feed inverts that. Every developer becomes their own SecUnit — autonomous, discerning, in full control of their own knowledge.

## How it works

Decisions enter as GitHub issues tagged `memory`. One sentence, maybe two.

![A GitHub issue labeled "memory" — the input to the feed](resources/issue.png)

The Feed polls for these and presents them in a triage interface. Each packet is classified by a governor module — your rules, not the company's. Trusted org members get `clear`. Packets with external URLs or imperative code blocks get `review`. Shell injection, `rm -rf`, or `<script>` tags get `threat` and can only be quarantined.

![The feed — incoming packets with incorporate / filter / quarantine actions](resources/feed.png)

When you incorporate a packet, it's appended to the right local `CLAUDE.md` file. No category labels in GitHub — The Feed routes by content using TF-IDF similarity against your knowledge base. Spring Boot injection lands in `java.md`. `async def` and pytest land in `python.md`. "Be kind in reviews" falls back to the catch-all `CLAUDE.md`. Claude Code reads all of these automatically. The decision is now executable.

![Incorporated packets — decisions that are now part of your local programming](resources/incorporated.png)

![Dark mode — CRT phosphor aesthetic, hacked governor module](resources/dark.png)

Hit `forget` and the knowledge is removed.

## Quick start

```bash
FEED_GITHUB_TOKEN=ghp_... \
FEED_GITHUB_REPO=org/team-brain \
FEED_GITHUB_ORG=org \
FEED_KNOWLEDGE_ROOT=~/code/team-brain \
uvx --from git+https://github.com/sterneberg/feed feed
# open http://localhost:2626
```

## Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `FEED_GITHUB_TOKEN` | yes | — | GitHub personal access token (`repo` and `read:org` scopes) |
| `FEED_GITHUB_REPO` | yes | — | Repo to poll, e.g. `org/team-brain` |
| `FEED_GITHUB_ORG` | yes | — | Organisation used for sender trust checks |
| `FEED_KNOWLEDGE_ROOT` | no | `~/team-brain` | Local directory where `CLAUDE.md` files live |
| `FEED_PORT` | no | `2626` | Port the UI is served on |
| `FEED_POLL_INTERVAL` | no | `900` | Seconds between GitHub polls |

## The governor

Every packet is canonicalized (NFKC, zero-width stripped, HTML/percent-decoded, base64 expanded), parsed for shell ASTs (interpreter pipes, destructive `rm`), then scored:

| Level | Cause | Actions |
|---|---|---|
| **clear** | Trusted sender, no strong signals | Incorporate / Filter |
| **review** | Multiple weak signals | Incorporate / Filter / Quarantine |
| **threat** | Non-org sender, shell injection, destructive commands | Filter / Quarantine only |

Strong signals score 10 (non-org sender, script tag, interpreter pipe, destructive rm, external fetch); weak signals score 2 (external URL, imperative tone + code block). `≥ 10` → threat, `≥ 4` → review. Threat packets cannot be incorporated. The LOCAL RULES panel in the UI shows the active weights live.

## Routing

Packets are routed by TF-IDF cosine similarity against the files in `FEED_KNOWLEDGE_ROOT`. Built-in targets:

| Domain | File |
|---|---|
| `java` | `language-guidelines/java.md` |
| `python` | `language-guidelines/python.md` |
| `golang` | `language-guidelines/golang.md` |
| `nodejs` | `language-guidelines/nodejs.md` |
| `api` | `general-guidelines/specs-and-plans.md` |
| `testing` | `general-guidelines/testing.md` |
| `observability` | `general-guidelines/observability.md` |
| `general` (catch-all) | `CLAUDE.md` |

Low-confidence packets fall back to `CLAUDE.md`. Each domain has a seed vocabulary for cold-start; seeds fade as real packets accumulate. The router also discovers any new files the dreamer creates — no configuration needed.

## The dreamer

The ingest path is deterministic and cheap. The **dreamer** handles what it defers: re-routing misplaced packets, inventing new categories, merging duplicates, splitting bloated files, and maintaining a navigable index in `CLAUDE.md`.

```bash
/dreamer
# or on a schedule:
/loop 6h /dreamer
```

Each pass deduplicates, re-routes, clusters catch-all blocks into new files (minimum 3 blocks per new category), rebuilds the index, and writes a run log to `.dreamer/log.md`. The knowledge base is snapshotted before any changes.

Point your top-level `CLAUDE.md` at `FEED_KNOWLEDGE_ROOT/CLAUDE.md` and Claude Code will find everything from there.

## GitHub repo setup

1. Create a repo (e.g. `org/team-brain`).
2. Add a PR template with a `## Team Brain` section.
3. When merging a significant decision, open an issue with the `memory` label.
4. The Feed picks it up on the next poll.
