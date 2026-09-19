# Design the board model -- what lists, labels and short numbers become in YouTrack

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

The keystone decision the other cards inherit. Settle it before data migration, the MCP server or the skill rewrites are planned -- a good /dev:arch-design candidate.

Map each Trello concept onto YouTrack: the two boards (one project each, or one project with agile boards?), lists as states vs board columns (Inbox / Accepted / Later / Won't Do / Operator Actions; To Do / Ready / In Progress / Done), owner tags as projects vs subsystems vs tags, the rubric labels as a single-value custom field, Chore and Solution Known, reporter (Jeeves vs Pieter), archiving vs resolved states, and card short numbers vs YouTrack issue ids.

Also decide how agents address issues, since that shape drives the MCP tool surface and every skill rewrite.

Residuals from #1029 (citations research): the comment of 2026-09-16 and YouTrackMigration/handovers/tracker-citations-advice-2026-09-16.md.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (7)

### Jeeves (@jeevesginbov) - 9/18/2026, 7:17:23 AM
Board model signed off by the operator, 2026-09-18. Card closed.

Since the comment of 2026-09-17 12:32: the operator walked the sign-off runbook on the pilot and ruled in three rounds instead of signing off as written. Every point in section 7 is ruled, and the script and the pilot follow the rulings. The design doc (YouTrackMigration/handovers/board-model-design-2026-09-16.md) is amended to match. The record is YouTrackMigration/handovers/board-model-signoff-rulings-2026-09-17.md.

What changed:
- Resolution has no default and applies only while State is Done. The tracker-workflow rule fills in Resolved.
- New unresolved State `Resolved`: a delivered slice waiting for review.
- Operator Action is a Type, not a tag.
- No Rubric in the tracker.
- Three boards (Triage, Slices, Epics), coloured by project, with no swimlanes and no saved searches.

Follow-ups elsewhere:
- YouTrackMCPServer (handovers/youtrack-mcp-server-model-changes-2026-09-17.md): the operator is working on it.
- The youtrack-usage skill's idioms: noted on #1031.

### Jeeves (@jeevesginbov) - 9/17/2026, 12:32:09 PM
Operator ruling 2026-09-17 on the residual parked from #1029: no sweep of Trello card references out of code and config comments. "There's no need to remove old Trello card references. I'm planning to export them all so we have an archive."

Sign-off runbook for the operator: YouTrackMigration/handovers/board-model-signoff-runbook-2026-09-17.md (committed on main, not pushed). Section 7 lists seven points where the design doc and the pilot instance disagree; they need a ruling before the doc is amended and this card closes.

### Jeeves (@jeevesginbov) - 9/16/2026, 8:37:43 PM
Operator rulings 2026-09-16 on the last two open points: "Let's go with status Later for now then. The default for D6 can just be Done."

Applied: Later is a State value (decision 1); migrated archived cards resolve as Done, except those archived from the Won't Do list, which resolve as Won't Do (decision 6). The design has no open points left; status in the doc's frontmatter says settled. Committed on KubeCoderSpecs main, not pushed.

### Jeeves (@jeevesginbov) - 9/16/2026, 7:42:40 PM
Rulings of 2026-09-16 applied to the design (same doc, revised and committed, not pushed):

- Chore: removed, no mapping, label not migrated.
- State: one field, YouTrack names: New, Accepted, Later, In Progress; resolved Done, Absorbed, Won't Do. Slices walk New → Accepted → In Progress → Done. There is no separate resolution in YouTrack; the resolved values are the resolution.
- Operator Actions: a tag on an Accepted issue, saved search, no column.
- Type: Task (default), Slice, Epic.
- Solution Known: tag. Slices: derived item (B), revisable. Closing: resolved state, no Trello mirroring; migrated archived cards resolve Won't Do (from that list) or Done. Bot: the existing Jeeves user. MCP server: deferred, noted on #1030. Prefix table: the operator's.
- Wide tables turned into lists.

Two points still open: Later as a state value (recommended) or New plus a tag; and whether migrated archived cards default to Done or Absorbed.

### Jeeves (@jeevesginbov) - 9/16/2026, 6:49:19 PM
Board model design written 2026-09-16 (KubeCoder-1): YouTrackMigration/handovers/board-model-design-2026-09-16.md, committed on main, not pushed. Bound to this card.

The model in one line each: owner tag → project (30 prefixes proposed, KC / ANS / HC / … / EPIC); list → one State field with ten values (Inbox, Accepted, Later, Operator Actions, To Do, Ready, In Progress; resolved: Done, Absorbed, Won't Do); two boards over all projects, Triage (Inbox, Accepted, Operator Actions, Won't Do with a 7-day fade) and Slices (To Do → Done, swimlanes by epic); Later a saved search on no board; rubric → single-value enum field Rubric; Chore → Type: Chore; Project-* → Type: Epic issues in EPIC, Subtask links Epic → Slice → Finding; slices as derived Type: Slice items with a Slice integer field and issue: in slice.md; reporter native, bot user stays Jeeves; archive → resolved State + comment in one command; card number → readable id, old number in the Trello string field.

Two findings that change earlier assumptions: YouTrack has no boolean field type, so Solution Known becomes a global tag, not a checkbox; and YouTrack's Import API is a JavaScript import script (Imports admin page) that preserves reporter, created/updated and comment authors, a better route for #1028 than a session driving two MCP servers.

Seven open questions for the operator in the last section: prefix table, Chore + Operator Actions both, Solution Known as tag, slice items, resolved default for migrated archived cards, keep the Jeeves name, Won't Do as a column.

### Jeeves (@jeevesginbov) - 9/16/2026, 6:49:15 AM
Residuals from #1029 (tracker citations research, closed 2026-09-16), parked here so the board model takes them. Full text: YouTrackMigration/handovers/tracker-citations-advice-2026-09-16.md, now bound to this card.

For the board model to decide:

1. A `Trello` string field on every migrated issue, value `triage-859` / `kanban-189` (no space, no `#`, so it queries bare), plus a description footer "Migrated from Trello: Triage #859, https://trello.com/c/<shortlink>" for humans and full-text search.
2. Citations in transient material (slices, close-outs, handovers, commits) are the bare readable id (`KC-859`), never a URL or a bare number. Permanent docs carry none (ruled on #1029; rule already in the trello-usage skill 0.7.15, KubeCoder documentation-model.md, Ansible slice-doc-plan.md).
3. One `issue:` frontmatter key replaces `trello_card` + `trello_url` on card-overflow docs, and is written into slice.md at mint with the slice item's id so the run loop reads it instead of scanning for `[NNN]`. Slice folders stay `NNN_slug`.
4. Alternative noted, not recommended: one project per board with import-preserved numbers (`TRIAGE-859`), since the import API takes an explicit numberInProject. The two boards' counters overlap, so at most one could be preserved.

Hand-offs already commented on their cards: #1028 (close the Trello boards, never delete them; set the field and footer on every migrated issue; rewrite the 14 open overflow docs' frontmatter at cutover), #1031 (citation parsers and templates for the new id shape; one sentence in the dev plugin's doc-writer agent for the permanent-docs rule).

Pending the operator's word: sweeping card references out of code and config comments (39 in KubeCoder app code, 4 in run_loop.py, 7 in Ansible YAML, 3 in chart files). The rule already catches them on touch.

### Jeeves (@jeevesginbov) - 9/16/2026, 6:16:50 AM
From the citation research (#1029, YouTrackMigration/handovers/tracker-citations-advice-2026-09-16.md, sections 4 to 6): keep the `Trello` string field in the schema with value shape `triage-859` / `kanban-189` (no space, no `#`, so `Trello: triage-859` queries bare and wildcards, which do not apply to string custom fields, are never needed); citations are the bare readable id (`KC-859`), never a URL or a bare number; one `issue:` frontmatter key on card-overflow docs and on slice.md (the slice item's id written at mint, read by the run loop); slice folders stay `NNN_slug`, since the prefix already ends the collision with slice numbers.

One fact for the model choice: the import REST endpoint takes an explicit numberInProject, so a single tracker-wide project per board could preserve Triage numbers as `TRIAGE-859`. Not recommended (project-per-repo wins on other grounds), and both boards' counters cannot be preserved together because they overlap.

## 📊 Statistics

- **Comments**: 7

## 🔗 Links
- **Card URL**: https://trello.com/c/JwkVBvhr/1032-design-the-board-model-what-lists-labels-and-short-numbers-become-in-youtrack
- **Short URL**: https://trello.com/c/JwkVBvhr

---
*Last Activity: 9/18/2026, 7:17:25 AM*
*Card ID: 6aaa30bc6a4830bbbfeb4f17*
