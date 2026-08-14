# P7 review — round 2

**Readiness.** Round 1's one blocking finding is resolved, and resolved the right way: the
sentence asserting the image carries no estate facts and that everything beyond the clone arrives
as environment variables is gone (`argo-cd/design.md:88-93`), the surrounding paragraph reads as
one continuous thought without it, and `grep -rn "estate fact\|knows nothing" argo-cd/` now
returns nothing — the claim was deleted, not relocated. Deleting it costs the set nothing the
phase owed: the credential half survives where the plan's bullets put it, in D33
(`decisions.md:270-277` — "reads plain environment variables and is agnostic to the provider
behind them") and in design.md's identity table and its trailing paragraph
(`design.md:394-406`), and V21's "the same Secret carries the run's non-secret per-cluster
configuration" still lands in D33, flow step 4 (`design.md:336-339`) and the table's first row.
history.md's narrowing is a true claim, not a softer false one: `no cluster fact is committed in
ArgoCDTools` (`history.md:84-85`) checks out against the repo — a case-insensitive sweep for
Ceph/S3/zfs/age/`clusters.yaml`/`srvk8s` values in `/work/ArgoCDTools` finds only the env *name*
`HOMELAB_CEPH_KEY` in `tests/test_environment.py:25` and `image/terraform.rc:3`'s
`https://tfmirror.home/`, which is a provider-mirror host, not a per-cluster provider fact, so
the sentence's scope — set two clauses earlier as "the per-cluster provider facts the deploy CLI
injects from `clusters.yaml`" — holds exactly. The plan.md done-record addendum
(`plan.md:745-749`) states what the commit did and each of its three claims is true. No
deterministic gate is recorded green for this commit and this repo has no tooling, so I checked
the diff by hand: both >100-column non-table lines in the touched files (`design.md:282`,
`history.md:9`) are present unchanged at `8406cc9`, every added line is under 100, and the commit
adds and removes no link. One advisory finding, filed so it survives F1's closure rather than as
fix work.

---

## F3 — the set's only remaining image-contents statement is stale in F1's own direction

**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

With the F1 sentence deleted, what `argo-cd/` says the hook image contains is two pre-existing
claims and nothing else:

- `decisions.md:241-243` — "The image carries exactly the job: Terraform, terraform-backend-git,
  git, and the presync scripts — baked in".
- `design.md:88-90` — "the Dockerfile that bakes them into the dedicated hook image: Terraform,
  terraform-backend-git, git, the scripts — nothing else (D31)".

The shipped Dockerfile bakes four things past that list, each load-bearing:
`librados2`/`librbd1` (`/work/ArgoCDTools/Dockerfile:35-36`, the estate provider's `DT_NEEDED`
libraries, asserted at build time by `:89`), the step-ca root
(`/work/ArgoCDTools/Dockerfile:62-63`) and `image/terraform.rc` (`:70`, with
`TF_CLI_CONFIG_FILE=/etc/terraform.rc` at `:16`), the last two being what lets `terraform init`
reach `tfmirror.home` for `registry.terraform.io/pvginkel/*`.

Round 1 recorded this inside F1's body and correctly scoped it out: the text is pre-existing,
image contents are D31/design.md's standing content rather than this phase's mandate
(`plan.md:684-716` names four content bullets, none of them the image), and V09 checks the
Dockerfile, not the register. That scoping is unchanged and this is not fix work for P7. It is
filed once so that closing F1 does not close the observation with it — after this commit the
`argo-cd/` set contains no accurate account of what the image carries, which is the input a
future slice's doc pass would work from.

**Failure scenario.** None traced. An engineer who reads only `decisions.md:241-243` after a
step-ca rotation and skips `/work/ArgoCDTools/Dockerfile` reaches the same dead end F1 described,
but nothing in this phase's diff put that text there or made it more prominent, so it anchors
nothing and blocks nothing.
