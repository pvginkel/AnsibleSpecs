# Consult round 4 — slice 006

**Outcome: `complete`.** Nothing outstanding clears the blocking bar; the slice is now provable end
to end rather than owed.

## What changed since consult 3

Consult 3 answered `complete` with three criteria owed to two operator keystrokes. Both landed
overnight, so the owed half is no longer a promise — it is observable:

| Step | Evidence |
| --- | --- |
| Jenkins job created and built | `IaC/Charts` **#1 SUCCESS** (29s); `http://registry:5000/v2/charts-home/tags/list` → `{"tags":["1","latest"]}` — the enforced `:<build>` + `:latest` pair |
| HelmCharts pushed by the operator | `origin/main` = `3770fdf` (the P3 commit, rebased onto `e87150d`); reflog shows `pull --tags -r origin main (finish)` then the push, author/committer Pieter van Ginkel at 08:41 |
| Release deployed | `IaC/HelmCharts` **#5773 SUCCESS**; `charts-prd` Active, `deployment.apps/charts` 1/1, `service/charts` ClusterIP :80 |

Two carded items are settled by that: the non-fast-forward divergence (rebase done, clean push) and
the executable ordering of the keystrokes (job created → `Charts` already on origin → manual first
build → image → HelmCharts push). Ordering held in reality: the index was generated 06:39:32 UTC,
the deploy ran 06:44 UTC.

## The three owed criteria, settled by execution

I ran these myself rather than inferring them from the deploy being green.

- **V12 — DNS + TLS from the homelab CA.** `host charts.home` → `10.2.1.7`. `curl` **without** `-k`
  on `https://charts.home/index.yaml` → `200`, so the chain validates against this pod's trust
  store; `openssl s_client` shows `issuer=O=homelab-ca, CN=homelab-ca Intermediate CA`, valid
  `Aug 14 06:41:02 2026` → `Sep 30 2026`. Issuance is eventually consistent (the plan's own
  caveat) and it has converged.
- **V13 — both names, longest as primary.** The leaf's SAN block is
  `critical DNS:charts, DNS:charts.home`, matching `parse_server_names`' `-len(v)` sort. Both names
  answer at `10.2.1.7`.
- **V14 — a Helm client resolves the published chart.** From the `iac` sidecar:
  `helm repo add homelab-test https://charts.home` → `helm repo update` →
  `helm search repo homelab-test -l` lists `homelab-test/homelab-shared 0.1.0`, exit 0 (test repo
  removed again). Stronger than "something is served": the fetched
  `https://charts.home/homelab-shared-0.1.0.tgz` is
  `sha256 5405a96d4495721b1e9d487253922bc8bf8008aeb9128ae0eb395071a354f50d`, byte-identical to the
  committed `dist/homelab-shared-0.1.0.tgz` **and** to the `digest:` the served `index.yaml` names.
  Argo's repo-server doing the same under homelab-CA trust stays slice 009's A.5 item, as scoped.

`verification.json` now records all 19 items as verified, with those probes as their rationale. I
edited the three previously-owed entries only; the test agent's other 16 stand as written. Leaving
them `owed` would have closed the slice's acceptance record on a state that no longer exists.

## Judged against the plan

- **R1–R5** are delivered by P1–P4 and each has implementing work I can point at: the library source
  and the R5 pin in `charts/homelab-shared/`, the publishing pipeline in
  `tools/package-chart.sh` + `tools/build-index.sh` + `Dockerfile` + `Jenkinsfile`, the release in
  `charts/charts/` + `configs/prd/charts/`, R4 as a chart with no `dependencies:` block at all.
- **Every ruling holds**, including the two that are about authority rather than code: no agent
  pushed HelmCharts (V18), and the Jenkins job was the operator's to create.
- **No done-record admits an unaddressed leftover.** P4's one recorded exception (the TF-owned rbd
  `refute` cannot be forced to bite, because the mutation errors the render first) is explained, and
  the regression it guards is still caught as a red render.
- **No phase depends on something nothing produced.** P3 was written against `registry:5000/charts-home`
  as a pinned interface and P2 published exactly that.

## Mechanical residue fixed in this session

`plan.md`'s P4 done-record bullet on `tools/package-chart.sh`'s destination argument said check 1
packs everything "into an **empty** scratch store — which is what still makes it pack everything".
Commit `012a266` made that false: the skip is git-scoped, so what makes the scratch store pack
everything is that git carries nothing at that path — and `tests/publish.sh:92-93` deliberately runs
the script against a scratch store whose tarballs are *truncated rather than absent* and requires it
to refill them. The record therefore said two different things about the same mechanism (`:470-472`
had it right), which is exactly how a later phase would re-derive the existence-based skip that
round 2 caught. Reworded to state the git rule and cite the truncated-store block. Prose only, no
behaviour change; committed to `AnsibleSpecs` `main` along with the verification updates. Not pushed
— that is the operator's call.

Nothing else needed fixing: both repo working trees are clean, `git diff --check` was clean at
consult 3, and the four shell scripts parse (with `build-index.sh` dash-clean) — re-checked, not
assumed.

## Carded, not appended

1. **`resolve-helm-args prd/charts .` now crashes from this pod.** With `charts-prd` created, the
   namespace-exists guard at `resolve_helm_args.py:96` passes and `helm get values` runs; this pod's
   read-only kubeconfig cannot read release Secrets, and `:107` raises an uncaught `RuntimeError`.
   It is the same defect the test phase already carded (only `ImageResolutionError` is caught), but
   it now hits the *single-release* invocation that P3's done-record names as its gate — so a later
   agent following that record reads a permissions failure as a broken release. Pre-image the same
   command 404'd instead. Nothing in this slice's diff touches that file.
2. **The base image's stock `index.html` / `50x.html` are in the served docroot** — both `200` live.
   Cosmetic: helm fetches `/index.yaml` and the absolute tarball URLs and never these. The P2 r1
   reviewer logged it as advisory. Worth noting alongside it that the P3 plan bullet predicting `/`
   would answer with the welcome page is falsified live — `/` returns `404`, because
   `location / { try_files $uri =404; }` bypasses nginx's `index` directive. A one-line `RUN rm` in
   the Dockerfile closes both whenever the repo is next touched.

The still-open card about the architecture model is now actionable rather than pending: the
`charts` chart, the `charts-prd` namespace and the `charts.home` ApplicationService exist in the
cluster, so the `update-architecture` agent has something real to read.
