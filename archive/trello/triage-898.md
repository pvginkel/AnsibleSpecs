# Raise the go catalog toolchain's memory limit from 1Gi to 2Gi

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `pink_dark` Minor
- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

The `go` catalog toolchain sidecar is capped at 1Gi memory, set in HelmCharts' `charts/kubecoder/values.yaml` — a repo cannot override this limit itself. At that ceiling, HomelabTerraformProvider's cgo link step OOMKills the sidecar when `go test ./...` runs at default parallelism, because the provider links against Ceph's librados/librbd C libraries. As an interim workaround, the repo's `project.yaml` pins `test:` to `cexec go go test -p 1 ./...` — serialised, not the plain form — with the memory ceiling named in a manifest comment. At the ceiling, `build:` also runs under heavy reclaim pressure (402 reclaim events on a cold build, no OOM kill during build itself).

Consequence: until the limit is raised, this repo's test suite runs serialised instead of parallel, and any OOMKill of the sidecar also wipes the apt-installed Ceph headers/libs, breaking the next build.

Fix direction: raise the `go` catalog toolchain's memory limit to 2Gi in HelmCharts, measured as sufficient for the parallel cgo link. After the values.yaml edit lands, the sidecar pod needs a recreate to pick it up; the repo's `test:` override should then be dropped back to the plain `go test ./...` form.

Source: handovers/fleet-onboarding-close-outs/HomelabTerraformProvider.md — A1, Q1

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/8/2026, 7:08:01 AM
Both halves landed (fleet onboarding follow-up pass). The limit: HelmCharts 090ee77 (2026-09-08 04:18Z, wave 0) set the go catalog toolchain to memory: 2Gi; IaC/HelmCharts #6271 deployed it and the live catalog reads 2Gi. The drop: HomelabTerraformProvider 96aadde (wave 3, 07:06Z) — test: is `cexec go go test ./...` again and the workaround paragraph is gone. Proven in Ansible-2 on a fresh start: memory.max 2147483648, go sidecar 0 restarts (read from the pod spec during the run), three green runs after go clean -cache with oom_kill 0 throughout, 39 passed / 7 skipped (the TestAcc* set). Jenkins IaC/HomelabTerraformProvider #31 SUCCESS. Worth knowing: the parallel cgo link runs at the 2Gi cap with reclaim (memory.peak 2147 MiB, 38 max events) — about 900 MiB of it anonymous, the rest reclaimable page cache from build-cache writeback — so a heavier module would tip it. Separately, the Ceph headers still live in Ansible's root.setup and vanish on any sidecar restart (#899, Won't Do by the operator's Q12).

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/3Anbk4g3/898-raise-the-go-catalog-toolchains-memory-limit-from-1gi-to-2gi
- **Short URL**: https://trello.com/c/3Anbk4g3

---
*Last Activity: 9/8/2026, 7:08:01 AM*
*Card ID: 6a9ef375cccb59604068fbea*
