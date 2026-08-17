# Plan review — slice 015 webhook_relay, round 1

Reviewed: `slice.md`, `plan.md`, `verification.json`, `attachments/webhook-relay-consult.md`, and
the code every load-bearing citation points at. Four findings, ranked operator-decidable first.

---

## F1 — V05's second sentence has no artifact in this slice to judge it against (operator-decidable)

**Problem.** V05 carries R5 verbatim, including *"The secret is the same value as
`webhook.github.secret` in `argocd-secret` — one OpenBao leaf, not a second secret."* Nothing this
slice ships can establish that. The plan's own **Not in scope** says the ExternalSecret for the
shared webhook secret is 009's, and slice.md's Interlocks put the OpenBao leaf's value on the
operator. This slice produces a Go binary, a Dockerfile, tests, a README and an
`architecture.yaml` — no Secret, no ExternalSecret, no leaf.

**Evidence.** `plan.md:139-141` ("the ExternalSecret for the shared webhook secret are 009's");
`slice.md:82-83` (same); `slice.md:111-113` (operator writes the OpenBao secret value);
`verification.json` V05 vs. P1's outcome at `plan.md:99-106`, which enumerates what the phase
produces. The provable residue of R5 — the service holds no credential toward GitHub or the
cluster, and its only config is one secret plus two URLs — is a code property; the sameness of the
value and the singularity of the leaf are deployment-time properties of 009.

**Impact.** The test agent has to discharge V05 against a README sentence or leave it unmet. Which
half of R5 is 015's to prove is a scoping call on an operator-written requirement, so it is the
operator's to make, not the session's. Left as is, the slice either closes with an AC met on the
strength of documentation alone, or closes with an AC hanging that 009 was always going to satisfy.

---

## F2 — V04 and V01 contradict each other on the health path; the reconciliation lives only in plan.md

**Problem.** V04 carries R4 verbatim: refuse *"any path but the webhook path"*. V01 requires
*"Plus a health endpoint"*. Read literally, satisfying V01 breaks V04. `plan.md` resolves this —
*"Exactly two paths are served: the webhook path `/api/webhook` (ruling) and a health path"* — but
`verification.json` is the artifact the test agent checks off, and the reconciliation is not in it.

**Evidence.** `verification.json` V04 (`"any path but the webhook path"`) against V01
(`"Plus a health endpoint."`); the reconciling sentence is at `plan.md:127` inside P1's
constraints, not in any criterion.

**Impact.** A test agent probing the refusal matrix gets 200 on the health path and has two
defensible readings: mark V04 unmet against a service that is behaving exactly as designed, or mark
it met and silently narrow an operator-written refusal rule with no ruling behind the narrowing.
Both outcomes are wrong in a different direction, and there is no round after this one to catch it.

---

## F3 — V09's runtime-stage claim is not supported by the Dockerfile it cites

**Problem.** V09 asserts the image is *"built by a multi-stage Dockerfile from a golang:\*-bookworm
builder into a slim runtime stage carrying only the static binary"*, evidenced by
`DockerImages/backup-server/Dockerfile:1-29`. That file's runtime stage is not slim and does not
carry only the binary: it is `FROM debian` (the in-repo base image), then `apt install -y curl
ca-certificates unzip sudo`, then `curl https://rclone.org/install.sh | sudo bash`. The plan's Go
ruling compounds it by putting both halves in one sentence — *"Follow `backup-server`'s layout and
Dockerfile shape … into a slim runtime stage carrying only the binary"* — and P1 repeats the
pointer as `backup-server/Dockerfile:1-29`.

**Evidence.** `/work/DockerImages/backup-server/Dockerfile:12-23` (runtime stage: `FROM debian`,
apt layer, rclone install, then `COPY --from=builder`). Contrast the repo's other Go image, named
in the same ruling as the second precedent but cited nowhere:
`/work/DockerImages/iac-provisioner/Dockerfile:9-13` — `FROM debian:bookworm-slim`, `util-linux
ca-certificates`, binary — which is the shape V09 actually describes.

**Impact.** An executor told to follow a named file's Dockerfile shape will read that file. On the
estate's one internet-facing surface, the runtime image's package surface is precisely what the
consult's §2 parse-surface argument is about ("a static binary means no interpreter and no
dependency tree to patch", `plan.md:60-62`). The citation points at the counter-example, and V09
then judges the result by a standard the cited precedent does not meet.

---

## F4 — the consult is declared authoritative wholesale, and two of its five sections are superseded

**Problem.** `plan.md:6-7` calls `attachments/webhook-relay-consult.md` *"kept verbatim and
authoritative for why the relay is shaped this way"*, unscoped. P1 narrows to §§1–3 but closes with
*"Nothing in it needs re-deciding"* (`plan.md:104-106`), which reads back across the whole file.
§4 and §5 are both overridden by rulings the plan carries:

- §4 recommends the public DNS name `hooks.webathome.org`; the carried-in ruling is
  `deploy-hooks.webathome.org`.
- §5's cut line states *"the relay slice delivers the DockerImages image with its tests, **the
  chart fragment authored in ArgoCDDeploy (proven by `helm template`)**, and the O3/D39 doc
  updates"* — directly contradicted by the cut-line ruling at `plan.md:48-53`, which moves the
  chart fragment to 009 because `ArgoCDDeploy` does not exist yet.

**Evidence.** `attachments/webhook-relay-consult.md:126` (hostname suggestion) and `:157-159` (cut
line) against `plan.md:40-41` (hostname ruling) and `plan.md:48-53` (cut-line ruling).

**Impact.** slice.md orders the consult kept verbatim, so the stale text is not editable — but the
plan's framing of it is what points the executor at it. An executor reading §5 as authoritative
finds itself owed a chart fragment and a `helm template` proof that the plan's **Not in scope**
denies, and §4 hands it the wrong hostname for the README. The damage ceiling is low (the scope
fence and the hostname ruling both hold) but the confusion is paid by every session that opens the
attachment.

---

## Checked and clean

Recorded so the operator knows these were not skipped:

- **AC completeness.** R1–R7 map 1:1 onto V01–V08 (R6 split across V06/V07), in the operator's
  wording, with every clause carried — the header list, the concurrency, the `:7000` port, the
  4-second per-leg timeout, the four negatives of R2, the `ping` forwarding, the full R6 test list,
  all three R7 doc edits. No dropped or softened requirement beyond F1/F2 above. No doc-truth
  universals. V09–V13 cover this session's four rulings plus the 009 hand-off.
- **Every citation verified against source.** `tools/dockerfile_deps.py:21-28` is `iter_image_dirs`
  exactly; `Jenkinsfile:46` is the `utils.hasChanges("${img}/.*")` test exactly; `Jenkinsfile:100-101`
  are the two `registry:5000/${image}:` destinations exactly; `Jenkinsfile.architecture:32-36` is the
  `for f in */architecture.yaml` copy loop exactly; `CLAUDE.md:27-30` is the validator instruction
  exactly. In AnsibleSpecs: `argo-cd/decisions.md:542` is O3, `:382` is D39,
  `argo-cd/design.md:290-291` is the O3 sentence, `argo-cd/phases.md:85-86` is A.4's "homelab TLS"
  bullet. All exact.
- **Independently derived expectations.** `cexec go go version` → `go1.26.5 linux/amd64`, matching
  the plan's parenthetical exactly. `cexec iac ./scripts/arch-validate.py */architecture.yaml`
  exits 0 over the existing 22-file set today, so P1's second gate is green before the phase starts
  rather than pre-broken. `webhook-relay/` does not collide with any existing top-level directory,
  and creating it is genuinely the whole of pipeline registration — both globs pick it up with no
  edit, as claimed. The pinned contract also holds against the receivers' real shapes:
  argocd-server's `/api/webhook` and the ApplicationSet controller's `:7000` webhook port are both
  correct, as is GitHub's 10-second delivery window that the ~4s per-leg timeout is sized against.
- **`Target: ../DockerImages`** is a real sibling repo at `/work/DockerImages`, is where every
  deliverable in P1 lands, and matches the `../<Repo>` form used by slices 006–009 and 013.
- **Task shape `pre-settled`** holds. slice.md names the consult the authoritative design and R1–R6
  fix the functional contract clause by clause; nothing in P1 leaves the executor a design to make,
  and the plan still carries the investigation the executor needs (glob mechanics, layout
  precedent, gate commands, toolchain version) rather than assuming it.
- **Phase shape.** One phase, PR-sized (one new directory: service, tests, Dockerfile, README,
  `architecture.yaml`), judgeable on its own diff. No planned testing phase and no planned doc
  phase; R7 is routed to the run loop's doc phase, which is correct — `docs/slice-doc-plan.md`
  surface 2 is `/work/AnsibleSpecs/argo-cd/` (`decisions.md`, `design.md`, `phases.md`), so all
  three R7 edits sit inside that phase's remit, and the doc-writer gets its instruction from R7 in
  the plan's requirements section.
- **No doc-phase content in the plan.** No doc-deliverable section, no drafted prose, no
  doc-content attachment. No superseded ruling kept alive with a correction chained after it.
