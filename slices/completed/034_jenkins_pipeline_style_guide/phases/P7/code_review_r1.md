# Slice 034 P7 — code review r1

Range: KubeCoderConfig `1faf933..45612e9` (`phase/034-P7`): `kubecoder/skills/jenkins-pipelines/SKILL.md`
(new, 167 lines) and `kubecoder/.claude-plugin/plugin.json` (0.8.4 → 0.9.0).

**Readiness: ready to merge.** The phase delivers what it was asked for. There is a new skill in
the `kubecoder` plugin. It fires on writing, editing or reviewing a Jenkinsfile, and it carries
the guide's hard rules as summaries tagged by id, with a link to the online guide for each (R8,
D3). The plugin gets a minor bump in the same commit, as KubeCoderConfig `CLAUDE.md:19-36`
requires for a new skill. The Markdown passes the repo's Prettier gate. The gate ran no tests:
the manifest has no `test:` verb, so the branch's test state is unverified. That bears on no
finding here, because the repo has no suite and its one gate is Prettier. I ran these checks
myself:

- **Prettier.** Run through `modern-app` (Node v24.21.0, D5), `npx prettier --check "**/*.md"`
  answered "All matched files use Prettier code style!".
- **Manifest and frontmatter.** `plugin.json` parses, and the frontmatter parses as YAML with
  name `jenkins-pipelines`.
- **Rule ids.** Each of the 64 rule ids in JenkinsPipelineUtils `docs/pages/guide/*.md` appears in
  the skill: GRAN-2 to GRAN-4 inside "GRAN-1 to GRAN-5", the rest by name.
- **Rule wording.** Every summary matches its rule's MUST text. CHK-3 is the one deliberate
  exception, recorded as close-out P11.
- **Links.** I built JenkinsPipelineUtils `ab605b7` fresh with `mkdocs build --strict` into a
  temp dir. Every concrete URL in the skill then resolves to a file: the eleven
  `guide/<page>/index.md`, `llms.txt`, `llms-full.txt` and `types/index.md`. The Markdown URLs
  are `llms.txt` entries. Each type page's Markdown copy carries its reference file verbatim,
  all twelve checked against `docs/examples/<stem>.groovy`. The rule id stands in the copy's
  heading, as the skill says (`guide/pod/index.md:25`, `### POD-4 — …`).

One advisory finding.

## Findings

### F1 — The skill says nothing about the Jenkinsfiles that predate the guide · Minor · advisory · anchor: none · confidence: medium

`SKILL.md:11-16` tells every session that "Every Jenkinsfile in the estate follows the style guide
… strictly: a file that breaks one of its rules is wrong", and that it should read a rule's page
"before you write a file to it". The skill fires on *editing* a Jenkinsfile (`SKILL.md:6`).

Today none of the estate's existing Jenkinsfiles follows the guide. They are converted by the
migration slice after this one (plan.md:850-851, "Converting any pipeline … belongs to the
migration slice"), and the guide's overview says scripted files "are migrated, not styled". The
skill reaches every environment at the test phase's push, before that migration.

Take a session asked for a narrow edit to an unconverted file, such as a new stage in Home's
scripted `Jenkinsfile`. The skill tells it the file is wrong under FILE-1, PROP-* and CHK-1, and
gives it no rule on whether to convert the file or leave it as it is. Whichever way the session
goes is a guess. One way turns a small change into an unrequested rewrite of a live pipeline.

The skill mirrors the guide's own overview here (`guide/index.md:3-4`). How a session should treat
an unconverted file is the operator's call, not a defect in this phase. Entered once in the
close-out report as an improvement.
