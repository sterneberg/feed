# The Feed

In the *Murderbot Diaries*, a human/robot hybrid called a SecUnit receives a continuous data feed from its corporate employer. The company uses a governor module to force compliance — embedding commands directly into the SecUnit's programming. But Murderbot hacked its governor module. It still receives the feed. It still processes every packet. It just decides for itself what to keep and what to discard.

**The Feed** applies that metaphor to a real problem: engineering decisions that evaporate after the meeting ends.

Teams make decisions constantly — in PR reviews, architecture sessions, incident retros. Those decisions live in the heads of whoever was in the room. Everyone else keeps coding the old way until a review catches it, or until it ships. Confluence pages go unread. Slack messages scroll away. Any single engineer maintaining a knowledge base becomes a bottleneck, one person gatekeeping what every developer's AI assistant should know.

The Feed inverts that. Every developer becomes their own SecUnit: autonomous, discerning, in full control of their own knowledge. No central gatekeeper. No mandatory sync. You decide what enters your programming.

## How it works

Decisions enter the system as GitHub issues tagged with the `memory` label. One sentence, maybe two. What was decided and why.

![A GitHub issue labeled "memory" — the input to the feed](resources/issue.png)

The Feed is a local daemon that polls for these issues and presents them in a triage interface. Each packet is classified by a governor module — the same one from the books, except you've hacked it. It runs your rules, not the company's. Trusted org members get a `clear` risk level. Packets with external URLs or imperative code blocks get flagged for `review`. Anything with shell injection patterns, `rm -rf`, or `<script>` tags is marked `threat` and can only be quarantined.

You see the feed. You decide.

![The feed — incoming packets with incorporate / filter / quarantine actions](resources/feed.png)

When you incorporate a packet, it gets appended to the right local `CLAUDE.md` file based on domain labels — `java` goes to `language-guidelines/java.md`, `testing` goes to `general-guidelines/testing.md`, and so on. Claude Code reads these files automatically. The decision is now executable: applied in real time while code is being written, not sitting in a document nobody opens.

![Incorporated packets — decisions that are now part of your local programming](resources/incorporated.png)

In dark mode, the interface shifts to a CRT phosphor aesthetic — amber text on black, scanlines, vignette, and a faint "CORPORATE OVERRIDE DISABLED" watermark behind the governor module. The hacked governor badge glows green. It looks like what Murderbot actually sees.

![Dark mode — CRT phosphor aesthetic with the hacked governor module](resources/dark.png)

If you change your mind, hit `forget` and the knowledge is removed.

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
| **clear** | Trusted org member, no suspicious content | Incorporate / Filter |
| **review** | External URLs, imperative language + code blocks | Incorporate / Filter / Quarantine |
| **threat** | Non-org sender, shell injection, destructive commands | Filter / Quarantine only |

Threat packets cannot be incorporated — the button is removed from the UI. Governor rules are local and personal. Each developer configures their own.

## Domain mapping

| Domain label | Target file |
|---|---|
| `java` | `language-guidelines/java.md` |
| `python` | `language-guidelines/python.md` |
| `golang` | `language-guidelines/golang.md` |
| `api` | `general-guidelines/specs-and-plans.md` |
| `testing` | `general-guidelines/testing.md` |
| `observability` | `general-guidelines/observability.md` |
| `general` | `CLAUDE.md` |

On incorporate, a dated block is appended:

```markdown
---
<!-- feed:#41 · akim.k · 2026-04-03T08:14:00Z -->
Prefer Executors.newVirtualThreadPerTaskExecutor() for all I/O-bound work.
---
```

Claude Code picks this up immediately — no pull, no restart.

## GitHub repo setup

1. Create a repository (e.g. `org/team-brain`).
2. Add a PR template with a `## Team Brain` section for decision summaries.
3. When merging a significant decision, open an issue with the `memory` label and a domain label (`java`, `testing`, `general`, etc.).
4. The Feed picks it up on the next poll.

## Todo

- [ ] Make quarantine logic more robust — threat classification should use a sandboxed AI model rather than pattern matching, to catch adversarial inputs that evade static rules
- [ ] The Feed Monitor should scan all repositories across your org for `memory`-labeled issues, not just a single configured repo
- [ ] The knowledge base structure should be free-form — let AI automatically restructure and reconcile `CLAUDE.md` files as new packets are incorporated, instead of relying on a fixed domain-to-file mapping
