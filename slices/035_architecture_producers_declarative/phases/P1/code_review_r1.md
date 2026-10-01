# Code review — slice 035, P1, round 1

Range: JenkinsPipelineUtils `0965d41c..5c39ece` on `phase/035-P1`.

**Readiness.** P1 meets its outcome and may merge. `architectureProducer` gives Ruling D2's
three steps, each called in `script {}`, with no default for any argument and an error that names
the argument. The archive check is the collector's filter (`/work/Architecture/Jenkinsfile:75-78`).
I checked every pattern the 78 producers archive today, and every command line they run: each
can be written with these steps. That covers `gen-architecture --stage <s> --producer <id>` in
all 50 deploy files, Ansible's single named file, and IoTSupport's two named backend files. The
comma-joined pattern ElectronicsInventory uses becomes two list entries, and the shell globs
`arch-validate` takes still work, because it accepts any number of paths
(`aac-tools/image/arch-validate.py:40`). The guide changes stay within the phase. No rule
section changed. The J16 row reads "in the library" with 28 + 50 = 78 files. Both reference files
call the steps, the type pages drop "not in the library", and the types index types the five
apps' producers. I ran the docs lint myself (`kc project lint`): all examples, the two rewritten
reference files among them, pass the controller's linter. I ran nothing else. Two Minor
findings remain, both advisory.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**The archive check passes an entry that holds a comma, though `archiveArtifacts` reads a comma
as a pattern separator.** `collected()` splits each entry on `/` only
(`vars/architectureProducer.groovy:88-90`). `archivePattern` then joins the entries with `,`
(`:80`), and `archiveArtifacts` splits on that comma (Jenkins core `ArtifactArchiver` → `Util.createFileSet`).

Example: the entry `docs/architecture/a.yaml,*/architecture.yaml` splits into segments
`[docs, architecture, a.yaml,*, architecture.yaml]`. An `architecture` segment comes before the
last segment, and the last ends in `.yaml`, so the check accepts it. The archive then includes
`*/architecture.yaml`, which is the DockerImages case the check exists to refuse
(`vars/architectureProducer.md:80-81`, plan P1 "Later phases": "archive refuses a pattern with no
path segment exactly architecture"). The model is archived where the collector never looks, and
the build stays green.

Copying an existing producer by hand can produce such an entry: ElectronicsInventory's archive
today is one comma-joined string (`ElectronicsInventory/Jenkinsfile.architecture:39`). Both of
its halves are collected, so that particular copy is harmless. The doc comment on `collected`
("every file the pattern matches lies under a directory named `architecture`") does not hold for
such an entry.

The input is not one the plan specifies, and nothing calls the step this way yet, so the finding
is advisory.

### F2 — Minor · advisory · category: comment-prose · anchor: none · confidence: high

**The var page says an archive pattern that matches no file fails the build. With several
entries, that is false.** `vars/architectureProducer.md:82` reads "A pattern that matches no file
fails the build too."

`archiveArtifacts` gathers every pattern into one Ant FileSet. It aborts only when the whole set
is empty. Jenkins core `ArtifactArchiver.perform`: `if (!files.isEmpty()) { …archive… } else { …
throw new AbortException(NoMatchFound) }`. So `archive(files: ['backend/docs/architecture/*.yaml',
'frontend/docs/architecture/*.yaml'])`, with no frontend model, archives only the backend's and
passes.

A producer author reading the page could rely on `archive` to catch a missing model. In the
shapes the plan gives (`validate` before `archive`, with the same `files`), `validate` already
fails on an unmatched glob, because `arch-validate` opens each path. So the wrong sentence costs
nothing today, and the finding is advisory.
