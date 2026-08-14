# Slice 007 · P1 — code review, round 1

Branch `phase/007-P1` in `/work/ArgoCDTools`, `git diff a2bf3b4..516c580` (17 files, +598).

## Readiness

**Ready to merge.** P1's outcome — "four arguments accepted, the deploy repo checked out at exactly
the SHA it was handed, and terraform-backend-git listening with the run's state URL resolved" — is
met, and met the way the plan's rulings ask for it. The four-argument contract matches design.md's
Job skeleton in order and meaning (`presync/cli.py:22-25` against `design.md:361-363` plus the
namespace ruling), `hook.repo` is treated as a clone URL, which is what the ApplicationSet actually
supplies (`design.md:187`, `'{{ .repo }}'`, and the Charts fixture at
`tests/consumer/values.yaml:38`). The clone is `init` + `remote add` + shallow `fetch` of the SHA +
`checkout --detach`, with `rev-parse HEAD` re-asserting the SHA, so a branch or tag handed as
`hook.revision` fails the run (`presync/git.py:38-40`; `tests/test_git.py:33-42`). The backend URL
is byte-for-byte `deploy_cli/tf.py:59-68`'s query shape with the ruled key
`argocd/<repo>/<stage>/terraform.tfstate`, and the three `-backend-config` flags are `tf.py:139-151`
(`presync/backend.py:50-62`). `provide()` is `iac-impl:307-348`'s recipe faithfully — inherit the
environment, background the daemon, bounded probe, fail by address — with `PRESYNC_TF_BACKEND` as
the one knob the plan required so the proof bar can run from this pod at all. No estate fact is
committed anywhere in the repo (`grep` for a Ceph mon host, an S3 endpoint, `zfs_pools`, an `age1…`
recipient, a `.home` name: nothing), no `bao`, no hvac, no secrets manifest — V14's container-side
half holds.

The dispatch records no green gate against this commit, so I ran it: `kc project lint` and
`kc project test` are both `[ OK ]` from `/work/ArgoCDTools` (ruff check, ruff format --check,
22 unittest cases), which is V01's verb requirement. I also ran the entrypoint directly —
`python3 -m presync <repo> <sha> prd app-prd` with the credentials unset exits **1** with
`presync: GIT_USERNAME is missing from the run's environment` — so `__main__.py`'s
`PresyncError` → exit-1 translation, which nothing in the suite covers, is correct today; P2 owns
proving that discipline on both paths, so I am not carding it.

Three findings, all **advisory**: nothing here harms the product on merge. F1 is the one worth
reading before the test phase runs the live proof, because it can make an acceptance criterion
check off falsely.

---

## F1 — `git -c credential.helper=…` appends to the helper chain, so this pod's ambient helper answers the clone instead of `GITHUB_TOKEN`

- **Severity** Major · **Impact** advisory · **Anchor** repro-trace · **Category** functional ·
  **Confidence** high (witnessed)
- **Evidence** `presync/git.py:25-35` (the helper is passed as a single `-c` on the fetch);
  `presync/git.py:10-12` (the comment stating what the helper is for);
  `tests/test_git.py:55-65` (the only exercise of the helper, and it bypasses git);
  `/home/ubuntu/.gitconfig` → `credential.helper=store`.

git treats `credential.helper` as a **multi-valued** config key and queries the values in config
order until it has both a username and a password; a `-c` on the command line is *appended* to
whatever the system/global gitconfig already set, it does not replace it. Run in this pod:

```
printf 'protocol=https\nhost=github.com\n\n' \
  | GIT_USERNAME=x-access-token GITHUB_TOKEN=the-pat \
    git -c "credential.helper=$PRESYNC_HELPER" credential fill
```

returns the **real `ghp_…` PAT out of `~/.gitconfig`'s `store` helper**, not `the-pat`. Adding
`-c credential.helper=` before it — the empty value that resets the list — makes presync's helper
win and it returns exactly `username=x-access-token` / `password=the-pat`. So the helper string
itself is well-formed and git invokes it correctly; what is not established is that it is the helper
git *uses*.

Two consequences, and only the second is live:

1. **In the hook pod this is currently harmless.** P4's image is noble + git with no gitconfig and
   no `HOME` credential store, so presync's helper is the only one in the chain. It becomes a real
   failure the day the image, a mounted `HOME`, or a base-image `/etc/gitconfig` carries a helper:
   the run would then authenticate as whatever that helper knows — or fail with a credential error
   naming nothing — while `GITHUB_TOKEN` sat unused, and `require()` would not have caught it
   because the variable *was* present.
2. **The slice's own proof of V02 can go false-green from this pod.** V02 asserts "the clone
   authenticates via an inline credential helper, never a token-in-URL remote", and the plan's proof
   bar (ruling, 2026-08-14) is a real entrypoint run from *this* pod. Any such run against a private
   GitHub repo will clone successfully via the ambient `store` helper regardless of what
   `GITHUB_TOKEN` holds — a run with a deliberately wrong token would still succeed. The live proof
   therefore cannot distinguish "the helper works" from "the pod's own credentials worked", which is
   exactly the distinction V02 names.

The unit suite cannot see any of this: `tests/test_git.py:55-65` reconstructs git's
`sh -c '<helper> "$@"' <helper> get` invocation by hand rather than letting git perform it, and the
clone tests (`tests/test_git.py:31-53`) fetch from a local filesystem path, which never asks for a
credential.

## F2 — the state backend is brought up without checking the daemon's own environment arrived

- **Severity** Minor · **Impact** advisory · **Anchor** none · **Category** functional ·
  **Confidence** high
- **Evidence** `presync/backend.py:65-78` (spawn, then probe the port — nothing else);
  `presync/cli.py:30-31` (`require()` is applied to `GIT_USERNAME`/`GITHUB_TOKEN` only);
  `attachments/credential-inventory.md` (`SOPS_AGE_KEY`,
  `TF_BACKEND_HTTP_ENCRYPTION_PROVIDER`, `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS`).

`provide()`'s comment at `presync/backend.py:73-75` names exactly what the daemon needs from the
inherited environment — "the git credentials, the encryption provider and the age keys" — and the
run checks only the first of the three. A `argocd-hook-credentials` Secret that is missing
`SOPS_AGE_KEY` (or the encryption provider, or the recipients) still yields a daemon that binds
6061 and a `provide()` that returns happily; the failure surfaces later, inside a Terraform state
request, as a backend error rather than as V14's "fails the run by name".

This sits on a phase seam rather than inside P1's stated outcome: P1 owns bringing the backend up,
while P2's section owns the `require()`-by-name behavior and points at the inventory as "the whole
inventory". Flagging it only so P2's executor reads the inventory as covering the backend's three
keys and not just the provider credentials — the natural reading of P2's "the provider environment"
heading leaves these three owned by nobody.

## F3 — the ordering assertion in the missing-credential test cannot observe a clone

- **Severity** Minor · **Impact** advisory · **Anchor** none · **Category** functional ·
  **Confidence** high (mutation-tested)
- **Evidence** `tests/test_cli.py:68-74`, specifically `:74`; `tests/test_cli.py:56` (where
  `tempfile.mkdtemp` *is* patched, and it is not this test).

`test_a_missing_credential_fails_the_run_before_anything_is_cloned` ends with
`self.assertEqual(list(self.run_dir.iterdir()), [])`. `tempfile.mkdtemp` is patched only inside
`run_main` (`:56`), so in this test `main()` would clone into a fresh system temp directory, never
into `self.run_dir` — the directory is empty in `setUp` and stays empty whatever `main()` does. The
assertion is true by construction.

Confirmed by mutation: swapping `presync/cli.py:30-34` so `clone_at_revision` runs *before* the two
`require()` calls leaves all 22 tests green, including this one. The test's first two assertions
(a `PresyncError` naming `GIT_USERNAME`) do bite and cover V14's "fails by name"; only the
before-anything-is-cloned half of the name is unbacked.

---

*Not findings, recorded so the next round does not re-derive them:* `namespace` accepted and unused
is P3's by the plan; `STATE_REPO_URL`/`STATE_REPO_REF` as constants rather than Secret keys is the
plan's own done-record ruling and D32 fixes both estate-wide; the library chart still passing three
arguments is P5's, and nothing consumes `homelab-shared` 0.1.0 or the (unbuilt) image, so there is
no window in which the mismatch is live; the spawn branch of `provide()` is exercised only with
`subprocess.Popen` mocked, which is forced — `terraform-backend-git` is not on PATH in the `iac`
sidecar (plan, P1) — and the mock asserts the exact argv.
