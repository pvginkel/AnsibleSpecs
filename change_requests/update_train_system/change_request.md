# Update-train system — doctrine, KubeCoder contract, scheduler, archive sweep

**One line:** Codify the operator's cadence-based dependency-update doctrine and build the
automation that runs it: a nightly incremental scheduler that walks every non-archived
GitHub repo on its own interval, updates it inside a KubeCoder environment via a headless
Claude agent, records stats, and reports through the Telegram IaC bot.

Triage source: operator's design in chat 2026-07-03 (two turns), and the 2026-07 review's
tech-radar "update trains" entry (`../../reviews/2026-07-iac-review/tech-radar.md`).
Heavy dependency on KubeCoder (see Dependencies).

## Doctrine (from chat — the why)

Operator explicitly rejects Renovate/Dependabot-style continuous dependency PRs (bounded
visible queue over unbounded arrivals — progress illegible, "most demoralizing tech tool in
existence"). Doctrine: **bulk update at a cadence, battle-test, push out**; bigger items
(Angular, PostgreSQL, k8s) get their own planned lines. Very few pins by choice — only the
`kubernetes` Python client (documented in the k8s-upgrade runbook). Python deps use ranges
(`0.x.*` / `x.*`) + lockfile: the ecosystem's own update command *is* the bump mechanism.

Tiers (assigned per dependency by "who tests this, and what happens when it breaks?"):
1. **Own code** — ranges + lockfile, updated by the train, tests gate. Agent-runnable.
2. **Blast-radius infra** (k8s, Ceph, OpenBao, operators/CRD charts, TF providers) —
   pinned, upgrades are planned lines, dev-soaks-ahead. Never on the train.
3. **Blind-trust appliances** (guacamole, ubuntu:rolling, small upstream tools) — float on
   the weekly rebuild *knowingly*; breakage detected by use; rollback = previous retained
   image tag. Operator: "I don't have the capacity or will to test guacamole releases.
   Plus rolling Ubuntu I will accept blindly." The doctrine's contribution is making the
   blind trust explicit and listed, so "float without doctrine" stops existing.

version-poller's weekly time-driven image rebuilds are the chosen mechanism for images and
stay (its redesign doc's insight — watching direct deps gives false coverage — stands).

## The scheduler (operator's design — verbatim intent)

- Keeps a **"next run" date/time per repo**. Runs nightly (~02:00) with a bounded window
  (e.g. 4h max) — the **incremental progress model**: keep making forward progress until
  the window is up; next night, continue.
- Each run: (1) find all non-archived repos *without* a next-run date — if onboarded, run
  the update process against it; otherwise **report an error** (every non-archived repo
  must implement the doctrine). (2) Sort all repos by next-run; process each with a
  next-run in the past, in order. If a repo is now archived: skip, delete its next-run
  date, log a note.
- The interval lives in the repo's contract file as "**every N weeks**" (profile-derived:
  weekly / monthly / quarterly). An interval change applies only from the repo's *next*
  run.
- **All stats tracked in a database of the app** (next-run date, all runs, failures,
  runtimes, number of packages updated, …). JSON files on disk suffice. The dataset feeds
  report generation — delivered via the Telegram IaC bot (`../telegram_iac_bot/`).

## Per-repo update process (operator's design)

1. Create a new KubeCoder environment; if one already exists by the expected name it is
   stale — repurpose it (reset + reuse). Name: `<repo>-AutoUpdate`.
2. KubeCoder then: creates the environment including all its dependencies (tools and
   services); ensures it is fully configured (credentials to external services so
   integration tests can run); runs a build. This proves the environment functional and
   warms all caches (npm/poetry/uv/…).
3. If any of this fails: report, move to the next repo.
4. Delete the environment when done.
5. The update agent is **headless Claude via the JSON input/output stream interface** —
   one bounded session per repo per train, driven by the contract + an outdated report;
   structured verdict out (updated / tests pass-fail / majors flagged / blocked-on).

## The contract file

**`.kubecoder/config.yaml`** — NOT a new AIWorkflow artifact. Operator: "The JSON contract
isn't an AIWorkflow thing. Honestly primarily it's a KubeCoder thing, plus lint and test
additions." Extensions needed:
- Lint + test entrypoints (structured, per repo).
- A new entrypoint: "**is the environment as the app expects it**" (database, queueing
  system, …) — readyz-shaped. Probably too heavyweight to literally be the readyz, but the
  operator is "very open to integrating this into the readyz endpoint of the KubeCoder
  worker daemon."
- The update interval ("every N weeks") + doctrine tier/profile.
This same contract feeds other consumers: AIWorkflow run-slice **preflight** ("can be
automated if the building blocks are required per repo") and KubeCoder auto-preparing
environments on setup/reset. One contract, several consumers — but those integrations must
not gate the train.

## Gotchas (operator-identified)

- **Repos managed through another repo** (AnsibleSpecs → Ansible): needs a KubeCoder
  **redirect construct** — "if a user wants an environment for this repo, KubeCoder tells
  them: you don't want this one, you want that one — create it?" The updater uses the
  redirect to skip such repos.
- **True monorepos** (DockerImages — many applications, different stacks): same treatment
  as everything else, at far larger scale. **No multi-configuration-per-repo support** —
  "If I want to finetune, I move it to its own repo." (A backend+frontend app repo doesn't
  count as a monorepo.)

## Archive sweep

Applying the doctrine to **every non-archived repo** implies archiving a large number of
repos first — "that's fine and the right thing to do." An agent can inventory every GitHub
repo (last commit, deploy status, references) and produce a keep/archive proposal; the
operator disposes. Adjacent-but-separate: Triage card #90 (DockerImages label — local
gitblit mirror cleanup of deleted/renamed repos) — do not silently adopt it.

## Dependencies / sequencing

- **KubeCoder MCP server must work** — operator is adding this to the KubeCoder list
  himself; it is a prerequisite, not part of this bundle.
- Telegram IaC bot (`../telegram_iac_bot/`) for report delivery.
- From chat: run the **first train manually** (manifest script + hand-driven sessions)
  before building the orchestration — battle-test the doctrine before automating it.
- Doctrine home once codified: decisions.md (or successor doc) — the tier list and the
  "who tests this" rule.
