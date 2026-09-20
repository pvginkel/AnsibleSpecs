# P6 code review — round 4

Branch `phase/024-P6`, range `0d53256..HEAD` (`51af5aa`), target `../AnsibleSpecs`. **No fix round
ran and no commit landed since round 3**: `HEAD` is still `51af5aa`, byte-identical to the tree
round 3 read, and there is no `executor_result_r3.json`. The run log shows why — the review-funding
consult bailed out twice before it could rule (`log.txt` 15:27:22 and 15:30:58, both
`BAIL-OUT (blocked): the spec repo /work/AnsibleSpecs is on phase/024-P6, not main`), and each
resume re-entered at `stage review`. So this round is a third read of one unchanged commit, not a
review of new work, and rounds 2 and 3 carry the same finding against the same text.

## Readiness

**Ready to merge.** I re-derived the phase's gate from the tree rather than taking any prior round's
word, and both halves of the diff hold. The CA-root inventory: `find /work -name homelab-root.crt`
returns twelve paths — the canonical copy, nine regular files and two symlinks. All nine regular
files are `cmp`-identical to `ansible/roles/baseline/files/homelab-root.crt`, and they are exactly
the nine `decisions.md:166` now names; the two the record excludes are
`HelmCharts/charts/{jenkins,kubecoder}/files/ca/homelab-root.crt`, both `-> ../../../../homelab-root.crt`,
which is what the bullet's new clause says. Exactly five resolve to a `COPY homelab-root.crt` line
in a Dockerfile (`ArgoCDTools/aac-tools/Dockerfile:48`, `ArgoCDTools/argocd-hook/Dockerfile:66`,
`DockerImages/kube-coder-{dev-base:78,arm64-cross-toolchain:60,esp-idf-toolchain:53}/Dockerfile`),
matching "the five image copies". The counts at `:166`, `:171` and `:174` agree. The pin rule:
`ghcr.io/yannh/kubeconform:v0.8.0@sha256:…` (`HelmCharts/Jenkinsfile:63`) and
`ghcr.io/aquasecurity/trivy:0.74.0@sha256:…` (`DockerImages/Jenkinsfile:41`) are the only two
`@sha256:` references written anywhere in the estate's live config — every other hit is a test
fixture — so the third-party half names precisely what exists, and nothing under `registry:5000/`
is written as a digest. `decisions.md` carries no other `ArgoCDTools/image/` path and no
`terraform.rc` path list, so the `argocd-hook` folder move leaves nothing else stale in this file.
The plan's P7 rewrite is arithmetically right against the file it directs: the runbook's `md5sum`
block lists seven paths today (`step-ca-root-rotation.md:137-143`) and "All seven hashes must match"
at `:146`, so canonical + nine = ten, and the three new rows are the `aac-tools` one plus two.

**On the unverified gate state:** `/work/AnsibleSpecs` has no `.kubecoder/` at all, so this repo has
no suite and no linter — there is no gate whose absence bears on anything here, and every claim
above was checked by hand against the tree.

**On rounds 2 and 3's blocking finding:** I do not carry it forward as blocking. It is a real
observation and I have re-entered it below as advisory `F1`, with the ground for the difference.
Round 2's advisory F2 is close-out `B14` and round 1's are `B13` and `S5`; none are re-litigated
here.

## Findings

### F1 — the register's only word on image digests uses "pinned" in a sense HelmCharts' own tooling uses the other way
**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

`decisions.md:599` closes with *"Images we build ourselves are not digest-pinned: we control what
the tag points at, so which tag a consumer takes — floating or pinned — is the consuming site's
call."* That sentence is the register's sole statement about image digests — `grep -n digest
decisions.md` returns `:599` and nothing else. Elsewhere in the estate the same word names a
different thing: `HelmCharts/tools/migrate-release.py:342` calls its flag `--no-pin`, *"skip
image-digest pinning via resolve-helm-args"*, and that resolution
(`tools/chart_tools/resolve_helm_args.py:148`, `new_value = "@" + get_digest(image)`, emitted as
`--set '<path>=@sha256:…'` at `:155`) is what every HelmCharts release deploys with — so a
first-party pod spec on prd generally carries a digest. A reader who opens `kubectl get deploy -A`,
or who greps HelmCharts' tooling for "pin", meets the word in the second sense and the register in
the first, with nothing in `decisions.md` recording that the second exists.

Why this is advisory and not the blocking contradiction rounds 2 and 3 filed: the sentence defines
its own sense of pinning one clause earlier — *"pinned by digest … because an upstream tag moving
under a gate changes what the gate accepts without a commit here"* — i.e. a reference committed
here that a tag move cannot shift. `resolve_helm_args` is the opposite of that: it reads the tag
the consuming site wrote and resolves whatever that tag points at *now*, and `Jenkinsfile:189-191`
makes the moved digest the trigger to deploy. It is the mechanism that makes a floating tag work,
not a pin against one. Under the sentence's own definition the claim is true, and its operative
half — which tag form a consuming site writes — is demonstrably true in code:
`charts/kubecoder/values.yaml` floats eleven toolchain entries on `:latest` (`:351`, `:423`,
`:442`, … , `aac-tools` at `:609`) and pins four resolved tags (`:381`, `:406`, `:456`, `:485`),
each the consuming site's call, exactly as `:331-332` states the catalog's own rule. Nor does
`aac-tools` itself ever meet the resolver: `get_helm_images` walks `charts/<chart>/templates/`
only (`resolve_helm_args.py:41,56`), and the toolchain entries live in `values.yaml`, rendered
into a ConfigMap — so R4's floating tag is floating all the way to the pod. I can construct no
procedure that goes wrong by following the landed sentence: nobody is told to write a digest,
nobody is told to remove the resolution, and the rule a reader would act on — a new first-party
reference needs no digest — is correct.

What is left is a gap rather than a falsehood: doctrine records no deploy-time digest resolution
anywhere, so the estate's two uses of "pinned" sit unreconciled. Closing that means adding an
account of the HelmCharts deploy path to the register, which is a larger edit than R4's ruling
asked this phase for and is the operator's call, not this phase's.
