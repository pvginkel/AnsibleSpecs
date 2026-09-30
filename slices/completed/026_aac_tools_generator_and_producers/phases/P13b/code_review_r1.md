# P13b code review — round 1

**Ready to merge; no findings.** The Ansible branch (`b92d01a..HEAD`) is empty, as a sweep phase's is
(push-sweep attachment: the phase's work is the repos it pushed and their ledger rows). Each of the three
device carriers carries one commit: CalendarDisplay `718dba0`, PaperClock `4e65593` and Intercom `72ebe0f`.
In each, `Jenkinsfile.architecture` swaps `containerTemplates.python` for `containerTemplates.aac_tools`
and runs `arch-validate docs/architecture/*.yaml` in that container. The `lint` gate runs
`cexec aac-tools arch-validate docs/architecture/*.yaml`, and `.kubecoder/config.yaml` declares
`- use: aac-tools`. The "stdlib-only / plain python3" gate comments are rewritten, and `scripts/arch-validate.py`
is deleted. The deleted copies were byte-identical to Architecture's canonical script at `84ae5ad`, so
nothing was lost. `git grep arch-validate` in each tree finds only the new call sites and the
`SEED-NOTES.md` history line, which the plan keeps (plan.md P11 "Later phases"). I checked the ledger
and the done-record against live state and did not rely on the harness logs:
- Jenkins has Firmware/CalendarDisplay #58, PaperClock #115 and Intercom #81 as SUCCESS on the pushed shas.
  Each console prints `Success: Uploaded firmware version <sha>`, and Intercom prints it twice, for
  `HARDWARE_VERSION=1` and `2`.
- AaC #11, #15 and #25 are SUCCESS and ran `+ arch-validate docs/architecture/architecture.yaml`
  (`✓`) inside the `registry:5000/aac-tools` container.
- The pushes were serial: the pushes landed at 10:27:47, 10:34:15 and 10:45:10, and each came after
  the previous carrier's ledger row was committed as done (`b9a6db7` 10:34:11, `382c79b` 10:45:08).
- No foreign commit was pushed (Ruling F1). GitHub's PushEvent for PaperClock is `before=24fb9f4`, which is
  `HEAD~1`. The last recorded pushes of CalendarDisplay and Intercom ended at `28ad924` and `5afa1ca`,
  and each is its sweep commit's parent.
- The done-record's sweep-wide claim holds. On current GitHub trees, none truncated, none of the 27 carriers the
  sweep pushed carries `arch-validate.py` on its default branch. Only Ansible keeps its copy, pending `b92d01a`.
- Close-out A9 covers the three environments that gained aac-tools, and with A4–A8 it names every one.
