# P1 code review, round 1: podYaml templates and refusals

Range `e62b3dc..15812f9` on `phase/036-P1` (JenkinsPipelineUtils). Gate green on `15812f9` (input).

**Readiness: ready to merge.** The phase delivers its outcome and V05's library half. `sidecars()`
gains `helm`, `iac-toolchain` and `python`, each matching its describable: `alpine/helm:3.9.1`;
`registry:5000/kube-coder-iac-toolchain` with uid 1000 and `TF_PLUGIN_CACHE_DIR` empty;
`registry:5000/python` (`vars/podYaml.groovy:73-80` against `vars/containerTemplates.groovy:12-49`).
A null `env` value is refused with the entry's image and the variable (`:129-133`). A name that is
not an RFC 1123 label is refused at evaluation (`:104-108`). With derived names gone (`containerName()`
deleted), that check covers every `images:` container. The tests assert exact rendered YAML and
exact refusal messages:

- the 63/64-character boundary;
- leading and trailing `-`, upper case, `.`, `_` and a space;
- a nameless map, which would otherwise render as `"null"`, itself a valid label;
- the null env value.

A dropped check or a loosened pattern therefore fails a test. Removing the string `images:` form
was the executor's call (plan P1). A survey of every `podYaml(` call in `/work` and `/work/scratch`
finds no string entry and no unnamed map except `KubeCoder/Jenkinsfile:28`. The plan's P8 now says
P8 must convert that entry. The only job building that file is `KubeCoder/Build-Main` on `*/main`.
The three type pages' python bullets are deleted. POD-4's **Why** and the `containerTemplates` table
are updated. One stale line remains on podYaml's page (F1, advisory).

I also recorded a fact under P1's "Later phases" in the plan, for P4.
`IoTSupport/Jenkinsfile.architecture:22` writes `registry:5000/python` under `images:`. That image
now has a template, and POD-5 says to use it. This is not a P1 defect: the file still renders.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

`vars/podYaml.md:130` (served as `docs/pages/reference/podYaml.md`, a symlink to `vars/`) lists
`containerName` among podYaml's internals: "`sidecars`, `imageContainer`, `containerName`,
`containerLines` and `quoted` are its internals." This phase deleted `containerName()` from
`vars/podYaml.groovy` (diff hunk at old `:399-406`), and P1 rewrote this page. The page now names a
function that does not exist. No consumer codes against it (internals are declared off-limits), so
nothing breaks.
