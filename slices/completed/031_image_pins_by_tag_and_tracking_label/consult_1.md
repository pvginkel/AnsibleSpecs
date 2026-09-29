# Consult 1: completion check

**Outcome: complete.**

## Where each requirement landed

| Requirement / ruling | Delivered by |
|---|---|
| R1, D1 (pause lifted as a dry run, GC included) | P4 (`DRY_RUN`, `garbage-collect --delete-untagged --dry-run`), P7 (`registryCleanup.dryRun: true`, suspension dropped) |
| R2 (tags, never digests; the comment; D53) | P7 (RegistryDeploy's reviewed comment), P9 (D53 amendment, AnsibleSpecs `14308f1`) |
| R3 (matrix per-build tag, pin wherever a list exists) | P6 (DockerImages `dd8e7f4`) |
| R4, D2, R1-A1 (the label decides; per-series floor) | P1 (kaniko2 `trackingTag:`, `inBuildSeries`), P4, P5, P8 |
| R5 (tunnel-reclaim off `:latest`) | P2 (KubeCoderDeploy `3de9ea8`), P6's pin list |
| D3 (relay pin written by builds) | P3 (ArgoCDDeploy `0bacce1`), P6's pin list |
| Standing ruling: §4 and D53 move to match | P8, P9; a grep turns up no other copy of the old scheme (`No exotic schemes`, `^\d+$`) in DockerImages, argo-cd or Ansible docs |

I checked this against the repos. Neither registry-cleanup nor version-poller carries the regex or the fallback any more. All three pin lists exist with the paths P2 and P3 added. The CronJob drives `DRY_RUN`.

## Owed, but not by an implementation phase

- **Test phase** (Rulings R1-Q2, R1-Q3, D1): V01, V03, V04, V05's live Keycloak pin, V06's sweep across the other deploy repos, V09 and V17, plus the live halves of V13, V15 and V18.
- **Doc phase**, as the done-records say:
  - DockerImages `README.md:19-21` ("a matrix variant is pushed under its own tag");
  - `registry-cleanup/architecture.yaml:7-10`'s summary, which still states the old scheme;
  - the design doc's §8, which still says nothing of cleanup's dry run.
- For the test phase: the plan's step 3 cites `Ansible/tools/ai_workflow/track_build.py`, which no longer exists. The tool is on PATH as `track_build.py` (`~/.local/bin`, shipped from DockerImages `kube-coder-dev-local-home/`).

## Mechanical residue fixed here

- S2: KubeCoderDeploy `20e0f71`. `chart/values.yaml`'s header claims no default only for the chart's eight image pins. `kc project lint` and `test` are green.
- S6: DockerImages `18dadc8`. The lone-version-tag bullet is gone from §4's builds in use. The change is to the design doc only.

Both are struck in the close-out. I added a note to S4: P7's done-record already carries the correction, as its review r1 F1 note.

## Left in the close-out

B1, Q1, Q2, S1, S3, S4 and S5 stay as they are. Each is an operator decision (Q1, the tunnel-reclaim pin going stale on prd; Q2, dangling tags), out of scope (S1 argo-migrate; S5 is DI-5's numbers), or advisory (B1, S3). None of them is work the plan owes.
