# P2 code review — round 1

Range: KubeCoderDeploy `4bb7823..f6a8fba` (`phase/012-P2`), one file: `Jenkinsfile.promote`.

**Readiness: ready to merge.** The job does what P2's outcome and V15 ask. It reads the seven
pins from the promoted commit's `config/prd/values.yaml` (`Jenkinsfile.promote:84-86`,
`148-180`) and does not compute them from a build number. It creates each `prd-<n>` from `<n>`
before `prd` moves (`92-110`). It fast-forwards `prd` with no `+`, so the first run creates the
branch and a backward push is refused (`115`). It then writes and pushes the annotated
`release-<build number>` tag (`118-132`). Every refusal runs before the registry is touched: a
commit not on main, `prd` already at the commit, a non-fast-forward, an existing `release-<m>`
and a malformed pin (`39-86`). The job declares `disableConcurrentBuilds()` (`19`), has no
rollback or force parameter, and holds only the shared GitHub credential (`46`); it reaches
`registry:5000` anonymously with `crane --insecure`. Targeted checks:
- The Jenkins linter parse is clean ("did not contain the 'pipeline' step").
- The seven pins in `f6a8fba:config/prd/values.yaml` pass `prdPins`' regex under a YAML 1.1
  parse.
- The `k8s:1.35.5` image in `registry:5000` installs `git` (`alpine/k8s` layer) and `crane`.
- A scratch remote confirms the git mechanics: `ls-remote … refs/tags/release-1` does not match
  `release-11`, `prd` is created by the push, and a backward push is rejected.
- git 2.51 strips the token from the remote URL in `ls-remote` and `push` error output. The
  network steps outside `withCredentials` therefore leak nothing into the log.

Only the first real run tests the sandbox and the steps. P3 already carries that note.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**A promotion whose release tag fails to push cannot be completed by re-running the job.** If
*Recording the release* fails after *Advancing prd* succeeded (`Jenkinsfile.promote:115` then
`128-129`), `prd` already sits at the commit. The re-run stops at `Jenkinsfile.promote:72-74`
(*"prd is already at … nothing to promote"*), so the job never writes D48's `release-<m>` for
that promotion. The same state follows a push that GitHub applied but the client saw fail. Every
other partial failure converges on re-run: missing `prd-<n>` tags are created and existing ones
left, and an unpushed `prd` is pushed. D48 calls the tag *"the only durable record of when
anything was released"*, so in this case the record is lost unless the operator writes the tag
by hand. The plan does not specify recovery (P2: *"A failure at any step leaves the later steps
undone"*, which holds), so this is advisory.
