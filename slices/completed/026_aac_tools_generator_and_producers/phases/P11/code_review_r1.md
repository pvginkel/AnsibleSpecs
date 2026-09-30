# P11 code review — round 1

**Readiness: ready — signoff, no findings.** P11 is a sweep phase, and its `Target: root` diff is
empty (`b92d01a..HEAD` on `phase/026-P11`). Per the attachment's § A sweep phase pushes before its
own review, the work under review is three single-commit pushes and their ledger rows. The three
commits are DockerImages `df61622`, KubeCoder `5bbf14bf` and KitchenDisplay `067308b`. Each one
meets § Migrating a carrier:

- **Jenkinsfile.** Each `Jenkinsfile.architecture` swaps `containerTemplates.python` for
  `containerTemplates.aac_tools` and runs `arch-validate`. In DockerImages this includes the copy
  loop.
- **Local gates.** DockerImages' guarded `architecture` test now runs through `aac-tools`.
  KitchenDisplay's `lint` runs through `aac-tools`, and its `.kubecoder/config.yaml` declares
  the tool (the restart is close-out A4). KubeCoder had no gate that ran the script.
- **Instructions.** DockerImages' `.architecturerc:11` and `docs/alert-manager/plan.md:393` now
  name `cexec aac-tools arch-validate`, and so does KubeCoder's
  `docs/operations/pipeline-dependencies.md:27`.
- **Copies.** All three `scripts/arch-validate.py` files are deleted.

`git grep arch-validate` at each head finds no other live reference. The one remaining hit is
KitchenDisplay's `docs/architecture/SEED-NOTES.md:11`, the seed-time history line that P11's
later-phases note keeps.

What I checked, beyond reading the diffs:

- **Pushes (Ruling F1).** Each clone's `origin/main` reflog shows one fast-forward push, whose
  parent was already on origin: `221b012`, `772a35fd` and the clone-time `742c33e`. No foreign
  commit rode along.
- **Stop rules and ledger (D1/F5, V13).** The canary DockerImages was pushed at 00:08:57, and its
  collector (#2274) and site pin were done by 00:16. The KubeCoder + KitchenDisplay batch was
  pushed at 00:16:48. The builds `/work/scratch/p9-sweep/logs/carrier-*.log` records match the
  ledger rows:
  - DockerImages #2574;
  - AaC/DockerImages #172, AaC/KubeCoder #385 and AaC/KitchenDisplay #14;
  - Build-Main #558, whose pin `51b98b2` rolled kubecoder-dev Healthy;
  - AaC/Architecture #2274 and #2276.

  Each AaC console shows `+ arch-validate docs/architecture/…` in the `registry:5000/aac-tools`
  container.
- **KitchenDisplay stayed here legitimately.** `Firmware/KitchenDisplay` reads `disabled: true`
  now, and its last build is still #71 (FAILURE).
- **V12 for these three.** GitHub's recursive trees of the three `main`s are not truncated and
  hold no `arch-validate` path.
- **The migrated gates work.** DockerImages' gate, with its guard passing here, exits 0. So does
  KitchenDisplay's lint statement (`✓ docs/architecture/architecture.yaml`).
- **The quiet gate can fail (mutation).** DockerImages' `--quiet` gate shape run on an invalid
  artifact exits 1 with `HTTP 400 … missing required field 'schemaVersion'`, so `--quiet` does
  not swallow a failure.
- **No environment silently loses the DockerImages gate.** Four environment configs on disk
  carry DockerImages: Ansible, KubeCoder, DHCPApp, and a stale scratch clone of AIWorkflow. The
  first three declare `aac-tools`. AIWorkflow's `origin/main` no longer carries DockerImages.
  So no environment turns the guarded gate from a run into a silent skip.

Close-out N5 already records the one procedural gap: KubeCoder was pushed without its devlock.
It is not re-reported here.

## Findings

None.
