# P8 code review — round 1

Range: `/work/Architecture` `843d79a..ae5107f` (`phase/026-P8`, one commit).

**Readiness: ready to merge.** The phase meets its outcome. No producer-facing text in Architecture
still tells a producer to copy the script: a grep for `scripts/arch-validate` and for re-copy or
drop-in wording finds nothing. Those places now name `arch-validate` from the aac-tools toolchain,
both in Jenkins (`containerTemplates.aac_tools`) and in KubeCoder (`cexec aac-tools`). The manual's
Jenkins snippet matches the shared library's `aac_tools(String name)`
(`JenkinsPipelineUtils/vars/containerTemplates.groovy:33-34`) and ArgoCDDeploy's working
`Jenkinsfile.architecture`. The "byte for byte" and "md5-pinned" claims hold: both copies hash
`9e7e3f8c…`, and `ArgoCDTools/aac-tools/tests/test_image.py:20,64` pins that hash.

The update agent's new Inputs item 4 (`update-architecture.md:48-51`) is wired end to end:
- Central update clones live under `/tmp/architecture-update/repos/` (`tooling/fleet.py:88`), and
  sessions run in-pod through `kc session create-headless --cwd` (`fleet.py:827`). I ran
  `cexec aac-tools gen-architecture --help` from a directory at that path, and it printed the
  contract with exit 0.
- The manual's stdin form works, and so does its `env VAR=…` form.
- `arch-validate` accepts `--json` and `--quiet`.
- `- use: aac-tools` is the catalog's form (`kc catalog` lists `aac-tools`).

The canonical `.claude/architecture/arch-validate.py` stays. V08 and V14 are covered; V09 is owed,
as the plan says.

## Findings

### F1 — The update agent's `--help` contract can be older than the generator the deploy repos build with · Minor · advisory · anchor: none · confidence: high

`update-architecture.md:49-50` says `cexec aac-tools gen-architecture --help` "prints the contract of
the aac-tools toolchain's generator, which the deploy repos build with". The two can differ:
- The deploy repos' AaC builds pull `registry:5000/aac-tools` untagged with `alwaysPullImage: true`
  on every build (`containerTemplates.groovy:34`).
- The Architecture environment's sidecar carries the image pulled at its last pod start. The plan
  records this (`plan.md:219-221`), and on 2026-09-25 the sidecar was witnessed older than the
  published generator. The central update's sessions run in that pod (`fleet.py:827`).

After any later ArgoCDTools publication that changes the judgment-layer contract, every central
update session reads the older contract until the Architecture environment restarts. Its edits to
a deploy repo's `architecture.yaml` can then miss or misuse a key that the published generator
reads. The AaC build and the red-build resume path catch an edit that breaks generation. They do
not catch an edit that is valid but incomplete.

This is a property of the mechanism the plan chose (Settled: "The Architecture repo's KubeCoder
environment gains the aac-tools toolchain"), not a departure from it, so it is advisory. It is
entered in the close-out's Suggestions.
