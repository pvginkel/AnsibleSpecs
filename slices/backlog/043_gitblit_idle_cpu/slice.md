---
issue: ANS-194
---

# 043 — Gitblit idle CPU

The `gitblit-app` container in `git-sync-prd` (GitSyncDeploy) burns 0.5–0.8 core around the clock
while idle — the bulk of a node's idle load — for a read-only mirror synced once a day (ANS-176).

Source: triage 2026-10-02 of the ANS intake queue. Card: ANS-176. The phase count triage guessed
(~3) is a guess from the card alone; triage found no neighbouring subject to group it with.

## Requirements

1. **ANS-176 — Gitblit near-idle when idle.** "That's high for a read-only mirror synced once a
   day. Find what it spends the CPU on (Lucene indexing, a ticket or federation poll, a GC loop,
   the MCP server's queries) and bring it down to near-idle. Possibly connected to the gitblit
   index work in slice 028 (ANS-118)."

## Operator rulings and Q&A

- No ruling at triage. No standing-decision collision found.

## Source material

The cards as read at triage on 2026-10-02, verbatim (headings demoted one level). A card's
diagnosis, cause or line reference is the card's claim, not verified at triage.

### ANS-176 — Gitblit burns 0.5-0.8 core continuously while idle

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Updated: 2026-10-01
- Links: Relates: ANS-118

#### Description

Seen 2026-10-01 while investigating a CPU spike (that spike was the slice 035 build wave, not this).

The `gitblit-app` container in `git-sync-prd` (GitSyncDeploy) uses about 0.5-0.8 cores around the clock, across every pod revision for at least the past week (Prometheus `container_cpu_usage_seconds_total`, 6h steps). On 2026-10-01 it averaged 488m over 30 minutes. `gitblit-mcp-server` uses about 27m and nginx nothing. This is the bulk of a node's idle load: about 0.9 cores of srvk8s2's 3 vCPUs before the pod moved to srvk8s1. The container requests 600m and 4Gi.

That's high for a read-only mirror synced once a day. Find what it spends the CPU on (Lucene indexing, a ticket or federation poll, a GC loop, the MCP server's queries) and bring it down to near-idle. Possibly connected to the gitblit index work in slice 028 (ANS-118).

#### Comments

none
