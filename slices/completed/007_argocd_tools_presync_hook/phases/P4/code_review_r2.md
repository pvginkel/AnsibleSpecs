# Code review — slice 007, phase P4, round 2

`git diff 9119be5..fce746a` on `phase/007-P4` in `/work/ArgoCDTools` (1 file, +15/-2). The rest of
the branch (`dc291c4..fce746a`) was reviewed in round 1 and is context here.

## Readiness

Round 1's single blocker is closed, and closed at the level it was raised: the image now installs
`librados2` and `librbd1` (`Dockerfile:35-36`), and I verified the consequence rather than the
package list. Two builds of my own, both green. First, `kaniko --context . --no-push` against HEAD:
the build-time assertion at `Dockerfile:84-89` runs as `USER ubuntu` and both `CDLL` loads succeed,
with `terraform version` / `git --version` still passing in the same layer. Second, a throwaway
`ubuntu:noble` probe that installs only that package pair, pulls the published provider from the
mirror this image points at, and **executes** it — the exact step round 1 showed dying at
`exit 127`:

```
=== exec provider ===
This binary is a plugin. These are not meant to be executed directly.
Please execute the program that consumes these plugins, which will
load any plugins automatically
provider exit=1
```

That is the plugin's own guard, past the dynamic loader, so every `DT_NEEDED` entry resolved and
noble's `librados2` 19.2.3-0ubuntu0.24.04.3 satisfies the binary's versioned-symbol requirement.
I also confirmed the fix is complete rather than partial for this provider: the estate provider
links go-ceph's `rados`/`rbd` bindings only (`/work/HomelabTerraformProvider/internal/cephconn/conn.go:9-10`,
`internal/rbdimage/client.go:6`), its `cephfs/admin` path rides rados mgr commands rather than
`libcephfs` (`internal/cephfssubvolume/client.go:6`), `rgw/admin` is HTTP, and the tree shells out
to nothing (`grep exec.Command` across the provider: no hits) — so librados+librbd is the whole
native surface, which is why the released binary starts here. Of the other four providers deploy
repos declare (`/work/HelmCharts/_providers/providers.tf:20-35`) none is cgo. The added comments
are why-comments, each factually correct — "at apply, never at init" is what round 1 established
and what the phase's own `init`-only proof empirically demonstrated — and they narrate no change
history. Package placement (before the HashiCorp suite is added, from the base image's own
sources) is proven by both builds resolving them. One Minor advisory finding, in the phase record
rather than the code; nothing blocks.

## Findings

### F1 — The done-record's mutation claim is not what the packaging does (Minor, advisory, anchor: none, confidence: high)

`plan.md:572-574` records the new assertion as "mutation-confirmed to fail the build when either
package is dropped". Only one of the two directions can fail. On noble, `librbd1` depends on
`librados2`, so removing `librados2` from `Dockerfile:35` still installs it transitively and the
`CDLL('librados.so.2')` load at `Dockerfile:89` still passes. Witnessed in the probe build above,
whose apt line named `librbd1` and not `librados2`:

```
=== dpkg -l librados2 ===
ii  librados2      19.2.3-0ubuntu0.24.04.3 amd64   RADOS distributed object store client library
=== CDLL librados.so.2 with only librbd1 requested ===
librados.so.2 LOADED
```

No product consequence: both packages are listed, the assertion still bites on the case that
matters (the libraries actually absent from the image), and the image I built carries them. What is
wrong is the strength attributed to the proof in a record later phases read.
