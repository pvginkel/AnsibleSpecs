# Code review — slice 024, phase P7, round 1

Branch `phase/024-P7`, `git diff ebff17a..f3cdc60` — three files: `.kubecoder/config.yaml`,
`docs/runbooks/step-ca-root-rotation.md`, `docs/runbooks/operator-workstation.md`.

## Readiness

The phase's substance holds against the filesystem it describes. All ten paths in the rewritten
`md5sum` block exist as regular files and hash to one value (`aa4e1a5c…`); `find /work -name
homelab-root.crt` returns exactly those ten plus HelmCharts' two symlinks, so "nine out-of-repo
copies" and "all ten hashes must match" are both true; the four `terraform.rc` paths exist and hash
to one value (`f2af2394…`), with only ArgoCDTools' moved, in both runbooks; the five-baked-copies
rebuild caveat matches the five `COPY … /usr/local/share/ca-certificates/` Dockerfiles; and the two
new DockerImages rows' claims check out (`kube-coder-arm64-cross-toolchain/Dockerfile:1,60,65` —
`FROM dockcross/linux-arm64`, `REQUESTS_CA_BUNDLE`; `kube-coder-esp-idf-toolchain/Dockerfile:7,53,58`
plus its `build-matrix.json`). `pvginkel/Architecture` is declared, and the checkout's origin matches
the URL. Nothing here is blocking. Three advisory findings: one behavioural side effect the
`repos:` declaration brings with it and that no record in the slice mentions, and two statements
newly written into the rotation runbook that are not true.

## Findings

### F1 — the new `repos:` entry makes every pod start report a failed setup step · Major · advisory · anchor: repro-trace · confidence: high

`.kubecoder/config.yaml:21` declares `pvginkel/Architecture`. Pod start runs the `setup` verb in the
primary repository **and in every extra `repos:` checkout that has a `project.yaml`**, each its own
step in the environment's setup status, and a failing one is reported as a warning naming
`cd /work/<checkout> && kc project setup`
(`/work/KubeCoder/manual/docs/reference/project-yaml.md:60-62`, `:260-263`). Architecture's manifest
sets every setup statement in the `modern-app` tool container
(`/work/Architecture/.kubecoder/project.yaml:25,41,49` — `cexec modern-app poetry install`,
`cexec modern-app npm ci` ×2), and this environment declares only `iac` and `go`
(`.kubecoder/config.yaml` `tools:`, and `kc env describe`).

Witnessed, in this pod, running exactly the command pod start runs for a checkout:

```
$ cd /work/Architecture && kc project setup
root: no setup statements — skipped
tooling: cexec modern-app poetry install --no-interaction    [FAILED]
cexec: tool "modern-app" is not available in this environment; the tools it has are: go, iac
exit=1
```

Failure scenario: the operator runs `kc env restart` (the restart this phase's own done-record hands
to them) → the Architecture checkout's setup step fails, at that start and at every start after it,
and the environment's setup status carries a standing warning. `setup` stops at the first failing
statement, so the `viewer` and `service` statements never run either — they would fail the same way.
No other checkout declared here has this property: HelmCharts' setup runs in `cexec iac`,
HomelabTerraformProvider's in `cexec go`, and the remaining repos declare no setup at all.

Advisory, not blocking: V17 asks for the declaration, and what to do about the consequence — carry a
`modern-app` sidecar in an 8 Gi pod, or accept a permanently red step — is an operator trade-off, not
an executor error. What is missing is that nothing in the phase's done-record, the close-out or the
config comment says the declaration brings it, so the operator meets the warning unexplained at the
next restart.

### F2 — the new inventory row names the homelab root as what gets a run to `architecture.webathome.org` · Minor · advisory · anchor: none · confidence: high

`docs/runbooks/step-ca-root-rotation.md:76`: "It is how a run reaches `https://charts.home` for the
chart dependency and `https://architecture.webathome.org` for the dataset and the validator." The
second half is false — that host serves a publicly-issued leaf, so the stock trust store reaches it
and the homelab root has nothing to do with it:

```
$ openssl s_client -connect architecture.webathome.org:443 … | openssl x509 -noout -issuer -subject
issuer=C=US, O=Let's Encrypt, CN=YE2
subject=CN=architecture.webathome.org
             # charts.home, same check: issuer=O=homelab-ca, CN=homelab-ca Intermediate CA
```

The slice's own record says so too — `verification.json` V14's evidence line ("architecture.
webathome.org serves a Let's Encrypt leaf (checked 2026-09-20)") — as does the image the row
describes: `/work/ArgoCDTools/aac-tools/Dockerfile:42-45` gives `charts.home` as the whole reason the
root is baked. A rotation operator reading this row puts the AaC dataset and validator inside the
blast radius of a root change they are not in, or blames a stale root for an `arch-validate` failure
that cannot have that cause. The same row's "which Jenkins pulls" is likewise ahead of the estate:
no pipeline consumes this image until slice 014 gives a deploy repo its `Jenkinsfile.architecture`.

### F3 — the `find` cross-check in the inventory section is off by one · Minor · advisory · anchor: none · confidence: high

`docs/runbooks/step-ca-root-rotation.md:67-68`: "a `find` that returns eleven paths is still this
nine plus those two links." A `find /work -name homelab-root.crt` returns twelve — the nine
out-of-repo copies, the two HelmCharts symlinks, and the canonical copy this same section names at
`:53-57`, which any such search matches. The sentence exists to settle a reader who counts more hits
than the table has rows, and it hands them the wrong number to settle on; the phase's own gate note
in `plan.md` records the real result ("returns exactly those ten plus HelmCharts' two symlinks").
