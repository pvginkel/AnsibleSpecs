# P3 code review — round 1

Range: JenkinsPipelineUtils `197b9a3..751d837` (branch `phase/034-P3`, one commit). Gate: green on
`751d837` (`gate_r1.log`), taken as given.

**Readiness: ready to merge, no findings.** P3 delivers its outcome. There is one hand-written page
per global var, at `vars/<name>.md` beside its code, and the site publishes all eight under a
"Library reference" nav section (`docs/mkdocs.yml:80-88`), reached through the
`docs/pages/reference → ../../vars` symlink.

- **Page accuracy.** Each page was read against its var. Every public method is covered, with
  correct arguments, return values and failure modes:
  - kubectl's 12 calls;
  - containerTemplates' 8 templates, and each one's `podYaml` equivalent (the derived names `helm`,
    `python`, `aac-tools` and `kube-coder-iac-toolchain` are right);
  - `helmCharts.kaniko`'s four call forms under Groovy's right-to-left default dropping;
  - the tracking-tag rules, which match `inBuildSeries`/`resolveTrackingTag`;
  - gitUtils' awk-pattern behaviour, already on record as close-out B1.

  Each page names the var's internals as outside the offer.
- **podYaml.** The page covers both `images:` forms and the unchecked RFC 1123 derived name
  (`vars/podYaml.md:52-81`), as the phase and 033 B3 require. Its inherited-template section
  matches `KubeCoder/Jenkinsfile:6-11`.
- **What Jenkins loads.** `vars/` still loads the same code. Upstream
  `SCMBasedRetriever.java:235` copies `src/**/*.groovy,vars/*.groovy,vars/*.txt,resources/`, so
  `vars/*.md` never reaches the controller. `LibraryCompileTest` filters `vars/` to `*.groovy`
  (`LibraryCompileTest.java:59-66`), and `exclude_docs` keeps the `.groovy` files off the built
  site; none is in `docs/site/`.
- **The test.** `check_site.py:51-75` pairs vars and pages both ways. I ran two mutations in a
  scratch clone of `751d837`:
  1. Adding `vars/witness.groovy` with no page: `--strict` stayed green (exit 0), and
     `check_site.py` exited 1, naming the var: "vars/witness.groovy: no reference page; write
     vars/witness.md …".
  2. Replacing the symlink with a real directory of copied pages: `check_site.py` exited 1 with
     "vars/<name>.groovy: its page reference/<name>.md is not vars/<name>.md" for all eight vars.

  So the test holds each page beside its var, not just somewhere on the site. The other
  directions (a page with no nav row, a page for no var) are witnessed in the done-record, and the
  code at `:67-70` agrees.

## Findings

None.
