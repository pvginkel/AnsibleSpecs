# P8 code review — round 1

Range: `dee1c87253b5ed759f23611e37b3221f8592ecc2..cd4fdeda7dd0` on `phase/007-P8`
(one commit, one file: `docs/slice-doc-plan.md`, +19/−4).

## Readiness

**Ready to merge — no findings.** The phase's outcome is that a doc-writer for any argo-cd slice
learns from `slice-doc-plan.md` that `/work/AnsibleSpecs/argo-cd/` is a surface it owns, and that
its `decisions.md` is not the homelab one. The diff delivers exactly that and nothing else: a new
surface 2 at `docs/slice-doc-plan.md:21-34`, placed adjacent to surface 1 where the confusion
happens, with the old surfaces 2–5 mechanically renumbered 3–6 (`:36`, `:45`, `:50`, `:55`) and no
other text touched. Every one of the plan's four owed elements is present — the five files by name
(`:22`), authority bounded by the migration's completion (`:23-25`), the trigger for when a slice
owes an edit (`:29-32`), and the explicit distinction from surface 1 (`:25-27`). I checked the
prose's factual claims against the set itself rather than taking them: all five named files exist
under `/work/AnsibleSpecs/argo-cd/` and their one-word descriptions match `brief.md:4-7`'s own
framing of the set; the claim that `history.md` alone carries a narrative is what
`decisions.md:4-5` states from the other side ("Longer narratives live in `history.md`"); and the
"edit the entry, no supersession notice" convention is what P7 actually executed and what
`decisions.md`'s register form already shows — its `supersedes …` clauses (`:229`, `:247`, `:296`)
supersede pre-register artifacts (`archive/plan.md`, `archive/app-lifecycle.md`, the CR), never a
prior version of an entry, so the doc plan does not misdescribe the file it is instructing edits
to. The renumber was the one mechanical hazard, and it is inert: a repo-wide grep for surface-number
citations finds none in live docs — `CLAUDE.md:10` cites the file, the `dev:doc-writer` agent
contract reads the doc whole and names no surface, and the only numbered citations
(`slices/completed/013_.../consult_1.md:13,15`, `slices/completed/006_.../consult_1.md:75`) are
frozen slice records. Scope holds: `Target: root`, docs-only, working tree clean, nothing in
`ansible/`, `terraform/` or the architecture artifact touched, and no acceptance criterion outside
V22 is in this phase's reach. I also stressed the direction the rules ask for — whether the new
entry contradicts an instruction a reader arrives with. It does not: the `dev:doc-writer` contract's
own rule 3 ("state the current design as if it had always been true. No supersession notices")
agrees with surface 2 verbatim, and surface 1's "must say so, including that it supersedes what was
there" governs a different file under a different convention, which the entry's "a slice can owe an
edit to either, both or neither" already separates.

## Findings

None. Nothing in the diff is tagged blocking or advisory; the phase's gate state
(`root: no test statements — skipped`) is this component's deterministic result for a docs-only
change and is taken as given, not re-derived.

Two things I looked at and deliberately did not report, recorded so a later round does not
re-litigate them: the entry omits the frozen `argo-cd/archive/` folder, which is correct rather
than incomplete — it enumerates the five live files by name, and `history.md:4-5` already states
the archive is frozen until sign-off; and `docs/slice-doc-plan.md:32` is exactly 100 columns, which
is inside this repo's convention (`docs/` carries far longer lines routinely) and cosmetic either
way.
