# Research what to do with tracker references across the specs repos

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Card numbers and board URLs are cited all over the repos. Rough file counts mentioning trello today: KubeCoderSpecs 434, AnsibleSpecs 51, DockerImages 31, AIWorkflow 26, HelmCharts 18, KubeCoder 6, Ansible 6, KubeCoderConfig 1 -- plus commit messages, close-out reports, handovers, decisions.md and the agent memory files.

Research the options: rewrite references to the new issue ids, keep a Trello-short-number -> YouTrack-id mapping table and resolve on demand, or freeze old references as historical and only use new ids going forward. Output is a recommendation, not a mass rewrite.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (4)

### Jeeves (@jeevesginbov) - 9/16/2026, 6:49:22 AM
Closed 2026-09-16. Research delivered in YouTrackMigration/handovers/tracker-citations-advice-2026-09-16.md (now bound to #1032); every residual is parked on #1032 in the comment of the same date, with the hand-offs already on #1028 and #1031.

### Jeeves (@jeevesginbov) - 9/16/2026, 6:44:30 AM
Ruled 2026-09-16 (operator): "I don't really have a problem with references in transient places. I would suggest not to push back at that too much. I do want all references in permanent documentation (runbooks etc) removed. So my current steer would be to do handle this completely through prompt engineering."

Done the same day; part II of the doc (sections 9 to 12) rewritten to the ruling:

- Rule as prompt text, no gate or script: written into KubeCoderConfig's trello-usage skill as the last card convention (plugin 0.7.15, host-wide), KubeCoder docs/documentation-model.md beside "no slice numbers", and Ansible docs/slice-doc-plan.md under "What does not belong here". Transient material (slices, plans, close-outs, handovers, commits, chat) is unconstrained; the template edits proposed earlier are withdrawn.
- Permanent documentation swept: 50 references removed across KubeCoder (6 docs), Ansible (5 runbooks/docs, 3 role READMEs), DockerImages (alert-manager plan), AIWorkflow (README, 3 plugin docs, 6 rationale docs) and the onboard skill (2). Each edit keeps the sentence true; the openbao runbook numbers turned out to predate the shared board (Triage #20 is a KubeCoder card). Committed on main in each repo, not pushed.
- Left for the operator: one sentence in the dev plugin's doc-writer agent (workflow edit; wording in section 10). Left for the rule to catch on touch: comments in code and config (39 KubeCoder, 4 run_loop.py, 7 Ansible YAML, 3 chart files); one word makes them a sweep.

Part I (freeze, Trello field, closed boards) stands as-is.

### Jeeves (@jeevesginbov) - 9/16/2026, 6:26:08 AM
Part II added to the same doc (sections 7 to 11) at the operator's request: a proposal to stop referencing board cards in prose altogether.

Sampled 60 existing references; every one plays one of ten roles (requirement provenance, narrative provenance, deferral/re-carding, close-out disposition records, rulings quoted from cards, docs pointing at pending work, a rule's origin in plugin docs, code comments, commit messages, handover topic binding) plus the tool-written keys. In every role the text the number points at is already in the file, verbatim, by the workflow's own "quoted in, not just linked" rule; the number is a board coordinate that goes stale (archived, absorbed, re-carded, migrated).

Principle: the specs quote, the tracker links. Rule: a session-authored specs document names a tracker issue in exactly one place, the `issue:` frontmatter key (or `sources:` if slices get no tracker item); prose, R-lines, headings, dispositions, comments and commits carry no id, number or URL; operator-written text is quoted as is. Text is the join key: a full-text search on a requirement title or a close-out headline finds the issue; the filed finding's title is the entry headline verbatim and links to the slice item.

Cost: three template edits inside #1031 (triage skill's slice.md template and dump brief, close-out skill step 3 "carded, <date>" instead of id and URL, sweep_slice.py record strings) and an optional grep gate in the doc phase. Existing corpus untouched (part I's freeze). What is lost: one click from a spec to a card in the rare case a completed slice's source matters.

### Jeeves (@jeevesginbov) - 9/16/2026, 6:16:46 AM
Research done 2026-09-16 (KubeCoder-1). Doc: YouTrackMigration/handovers/tracker-citations-advice-2026-09-16.md (census, option table, per-card inputs, verified YouTrack facts).

Recommendation: freeze every pre-cutover citation as history; put the mapping in the tracker, not in a file (a `Trello` custom field with a `triage-859` / `kanban-189` token plus a one-line "Migrated from Trello: Triage #859, https://trello.com/c/..." footer on every migrated issue); close the Trello boards, never delete them, so the 281 distinct shortlink URLs keep resolving; rewrite only the live set (the 14 open card-overflow docs' frontmatter, at cutover, from the migration session that holds the map).

Mass rewrite refused: about 2,500 sites in about 500 files across eight repos; about 1,000 bare `(#NNN)` citations are ambiguous three ways (Triage number, Kanban number, slice number) so they cannot be rewritten mechanically; about 200 commit messages cite the same numbers and cannot be rewritten at all, so the corpus would end less consistent than it started.

Going forward: cite the bare readable id (`KC-859`), never a URL, never a bare number; one `issue:` frontmatter key replaces `trello_card` + `trello_url`, and is also written into slice.md at mint so the run loop reads the id instead of scanning for `[NNN]`; slice folders stay `NNN_slug`; the source dump keeps the verbatim text and drops the `URL:` and `List:` lines.

Inputs left as comments on #1032, #1028 and #1031. Card left in Inbox for your disposition.

## 📊 Statistics

- **Comments**: 4

## 🔗 Links
- **Card URL**: https://trello.com/c/wT4S19Hc/1029-research-what-to-do-with-tracker-references-across-the-specs-repos
- **Short URL**: https://trello.com/c/wT4S19Hc

---
*Last Activity: 9/16/2026, 8:53:29 PM*
*Card ID: 6aaa3001ae5a4ce3fd0d0cf5*
