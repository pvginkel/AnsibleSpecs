# P12c code review — round 1

**Readiness.** The Ansible range `b92d01a..HEAD` is empty, as the push-sweep attachment says a
sweep phase's `Target:` diff is. The phase's work is three pushed carrier heads and their ledger
rows, and all of it holds. ElectronicsInventory `55fb7b7`, ZigbeeControl `e6c9f76` and
IoTSupport `dc4260e`+`c38bd6f` each delete every copy of the validator. The five deleted copies
differ from Architecture's canonical script, which is byte-identical to the image's, only in type
hints and an `open(..., "r")`. So nothing needed carrying back. Every Jenkinsfile stage that ran a
copy now runs `arch-validate` in `containerTemplates.aac_tools`. IoTSupport keeps `python` only for
its generator stage, and both containers share the workspace, so `deployed-architecture.yaml`
reaches the validate stage.

ElectronicsInventory's two `lint` gates moved to `cexec aac-tools arch-validate
docs/architecture/*.yaml`. I ran both statements here from `backend/` and `frontend/`, and both
exited 0. Its `.kubecoder/config.yaml` declares aac-tools, with the restart in close-out A7.
ZigbeeControl's and IoTSupport's `project.yaml` lint gates never ran the copies (ZigbeeControl
`.kubecoder/project.yaml:42-45`, IoTSupport `.kubecoder/project.yaml:42-45`). `git grep` on the
three `origin/main`s finds `scripts/arch-validate.py` only in SEED-NOTES history and IoTSupport's
old feature records, and finds no stale "stdlib-only" or "python container" comments.

Ruling D6 is met. `c38bd6f` drops exactly the `somfy_remote` line. The Jenkins consoles of
AaC/ElectronicsInventory #26, AaC/ZigbeeControl #24 and AaC/IoTSupport #42 check out
`55fb7b7`/`e6c9f76`/`c38bd6f` and run `+ arch-validate …` inside the `aac-tools` container, all
`Finished: SUCCESS`. GitHub's recursive trees of the three `main`s (not truncated) hold no
`arch-validate` path. The push logs show each app build green, each pin Synced/Healthy, and
collectors #2310/#2314 with their site pins rolled. That matches the ledger rows and the done-record.

One advisory finding. Nothing is blocking.

## F1 — Close-out B2 stays live with a Consequence line P12c r2 made false · Minor · advisory

- **Category:** comment-prose · **Anchor:** none · **Confidence:** high
- **Evidence:** `close-out.md:229` has P12c r2's note that B2 is resolved (D6, `c38bd6f`,
  AaC/IoTSupport #42 green). `close-out.md:231` still reads "The sweep stops at IoTSupport, the
  last P12c carrier, so V12 cannot hold for it until the operator retires the device or rules
  otherwise." The entry is not struck, so `close_out.py list` shows that Consequence under a
  `· major` headline, and `counts` counts it as a live bug. The tool's `strike --reason` exists for
  this case: its help says "resolved/refuted names the commit and the re-run". It is the same
  pattern S13 records for B1.
- **Why it matters:** the operator triages from the list view. It presents a resolved blocker as
  an open major bug whose consequence says the sweep is stopped. The product is unaffected.
