# P4 — code review, round 1

`git diff d4db54a..d0dbfe6` on `phase/024-P4` (`/work/ArgoCDTools`): the handover-equality check,
its KubeCoder annotation fixture, a unit test pinning that fixture, and the two exclusion lists
(`.dockerignore`, `test_image.py`) that keep `checks/` out of the image.

## Readiness

Ready to merge. The phase's outcome — a repeatable check in this repo that proves R8 on the real
case — is met, and I confirmed it rather than taking the done-record's word: `cexec iac python3
aac-tools/checks/handover_equality.py` runs green here, reporting 9 elements and 16 relations on
both sides with the four cross-stage relations named as excluded, which is exactly the target
`attachments/handover-equality.md` describes. More importantly it is not a check that can only
pass. I falsified it three ways: re-minting the `NS` constant in a copy of the generator (the one
mutation R8 is about) produced 36 differences and exit 1; dropping the `kubecoder-mcp` line from the
fixture produced 4 (a minted duplicate service, two missing relations, a re-pointed `Assignment`)
and exit 1; and a dataset with one element's `label` mutated and one element planted reported the
field and the id and exit 1. The generator's envelope carries exactly the four element arrays
`ELEMENT_ARRAYS` names plus `relations`, and the published dataset has no KubeCoder element outside
those four, so the set-equality claim covers the whole surface on both sides. The phase's three
stated constraints hold: the check is outside `kc project test` (`unittest discover -s tests`
cannot reach `checks/`), it clones rather than writing into `/work/KubeCoderDeploy` (which is clean
at `ede0394`), and it runs the generator from source under `sys.executable`. Both findings below
are advisory nits; the fixture-drift hazard I would otherwise have raised is already recorded as
close-out **S4**.

## Findings

### F1 — the "one snapshot" the note promises is two fetches of the same URL · Minor · impact: advisory · anchor: none · confidence: high

`main()` fetches the dataset itself (`aac-tools/checks/handover_equality.py:247`,
`load_dataset(args.dataset)`) and then hands the child the same *URL*, not the bytes it read
(`:99`, `ARCH_DATASET_URL=dataset`). With the default `--dataset` (a URL) that is two independent
HTTP GETs at two different times, so a `helm-charts` publish landing between them still shows up as
a difference. The comment above the line states the opposite — *"Both sides read one snapshot, so a
publish between the two reads cannot look like a difference"* (`:97-98`) — and `plan.md:535` repeats
it as a settled property of the phase. The cost is not the race, which is rare and fails loudly; it
is that the note tells the next reader to rule the race out, so a spurious difference gets
investigated as a regression in the port. Only a file passed to `--dataset` gives the property the
note claims.

### F2 — the check cannot read a multi-document dataset the generator handles · Minor · impact: advisory · anchor: none · confidence: high

The check's `load_dataset` (`aac-tools/checks/handover_equality.py:122-127`) calls
`yaml.safe_load`, and its docstring calls that *"the generator's own rule"*. The generator's rule is
`yaml.safe_load_all` with every envelope in the stream added to the index
(`aac-tools/image/gen_architecture.py:489-491`); it mirrors the URL-versus-file half but not the
multi-document half. The endpoint serves one document today (555 KB, no `---` separators, read
2026-09-20), so nothing is wrong now; if it ever serves a stream, the generator keeps working and
the reference side of the check raises `ComposerError` instead. A loud failure, not a wrong result.
