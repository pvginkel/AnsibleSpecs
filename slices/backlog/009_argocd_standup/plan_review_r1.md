# Plan review — slice 009 argocd_standup, round 1

Reviewed: `slice.md`, `plan.md`, `verification.json`, the `argo-cd/` document set
(`phases.md` A.4/A.5, `design.md`, `decisions.md`), slice 007's `credential-inventory.md`,
slice 015's `slice.md` and relay consult, and the code the plan cites.

**What holds.** AC coverage is 1:1 and in the operator's wording: R1 fans out to V01–V06 without
losing a clause, R2–R18 map to V07–V23, the exit criterion to V26–V27, the relay ruling's two
added items to V24–V25. No requirement is dropped or softened without a ruling; no doc-truth
universals. `Target:` lines name real sibling repos (`/work/ArgoCDDeploy` exists with the seeded
`e8cb797`; `/work/HelmCharts` is the estate registry) and match the estate's `../Repo` convention.
No testing or doc phase is planned. No attachments, correctly: `design.md:155-273`, 007's
credential inventory and 015's consult are authoritative and the phases cite rather than restate.
Citations are unusually precise — `design.md:201-209` is exactly the four helm parameters,
`_tf-presync-hook.tpl:27,39,51` exactly the three hard-coded names, `_tf-presync-hook.tpl:45-48`
exactly the four `required` guards, consult `:78` exactly the payload-cap sentence. The
independent checks I ran confirmed the ApplicationSet template, the `argocd-hooks` hard-coding,
the 15-file glob with no `reconciler:` key anywhere, the bare `keycloak` provider with no
`keycloak_*` resource in the estate, the absent `integrations/github`, the Alertmanager null sink,
the `eso/prd/*` grant covering the new leaves, and that no `argocd*` namespace exists.

Four findings.

---

## F1 — A.5's throwaway deploy repo is build work with no phase, no gate and no reviewer · operator-decidable, blocking

**Problem.** A.5 opens with a build instruction, not an acceptance statement:
*"Use a throwaway app entry + tiny deploy repo; delete both afterwards"* (`phases.md:96`,
`slice.md:66`). Nine criteria — V15–V22 and V27 — can only be exercised against that repo. The
plan assigns producing it to the test phase in a single ordering bullet:

> **A.5 needs the disposable repo before the drill, not before any phase.** No phase targets it:
> the slice states the proof items are acceptance, not build work, so the throwaway app's tiny
> chart and Terraform are the test phase's to materialise into the repo the operator creates.
> — `plan.md:216-221`

The sentence it leans on is `slice.md:64` — *"These are the slice's outcome-level acceptance, not
extra build work"* — which governs **the proof items**, i.e. don't ship product features to
satisfy them. It does not govern the fixture A.5 itself mandates. The plan reads a scoping note
about deliverables as a licence to omit an artefact the requirement names.

**Evidence.** What the fixture actually has to be, read off the criteria it serves:

- a chart that includes `homelab-shared.tf-presync-hook` (V16, V17) and carries the `Prune=false`
  Namespace manifest (V18);
- a real `terraform/` — V17 is *"clone → backend → apply → exit code gates the sync"*, so an empty
  or absent Terraform directory proves nothing;
- `config/{stage}/values.yaml` reached by `../` (V15) and `*.tfvars` for the apply;
- a `Chart.yaml` dependency on `homelab-shared` from `https://charts.home`, which is what makes
  V19 observable;
- a `configs/prd/<app>/<stage>/release.yaml` added to HelmCharts `main` and later removed (V20,
  V27).

That is a deploy repo, not a test fixture. The plan's cited worked example does not cover it:
`/work/Charts/tests/consumer/` is `Chart.yaml`, `values.yaml` and seven templates — **there is no
`terraform/` directory**, so it is a render fixture and says nothing about V17's clone → backend →
apply path.

The receiving phase has no mandate for it either. The test phase's dispatch is "read
`/work/Ansible/docs/slice-testing-strategy.md` and execute it"; that document's five sections are
gates, static verification of the diff, read-only live checks, push, and the deploy-owed handover
— it contains no instruction to author a chart or Terraform, and §5 is explicit that the phase
"ends with work owed to the operator rather than a green tick". Separately, the repo the operator
creates (`e.g. pvginkel/ProofDeploy`, `plan.md:151-155`) is not in `/work/Ansible/.kubecoder/config.yaml`,
so it is not in the workspace at all.

**Impact.** Nine of twenty-nine criteria hang off an artefact that no phase produces, no
`kc project test` covers and no `dev:code-reviewer` ever sees. The run reaches the test phase with
the standup built and the proof of it unbuildable, and the exit criterion (V27) is unreachable.
This needs an operator ruling because either resolution moves the line the operator drew at triage
(*"G1–G7 as proposed — A.4 and A.5 stay one slice"*): the drill gets a phase of its own, or the
whole fixture becomes operator-owned work handed over deploy-owed.

---

## F2 — `is-public: "no"` does not produce homelab TLS; R5's TLS half fails silently · blocking

**Problem.** The plan states as an established estate fact:

> `is-public: no` gets a step-ca leaf via `https://ca.home/acme/acme/directory` and an
> `allow 192.168.0.0/16` block; `is-public: yes` gets Let's Encrypt and faces the internet.
> — `plan.md:106-109`

and instructs P1 accordingly: *"argocd-server gets `is-public: "no"`, a `.home` server name and a
step-ca leaf"* (`plan.md:258-259`). The configurator treats certificate issuance and the RFC1918
allow block as two independent switches. `is-public` drives only the second.

**Evidence.** `/work/DockerImages/nginx-configurator/app/nginxconfigurator.py:137-146`:

```
137  if entry.is_public:
...
144      ssl_ready = self._ensure_ssl_certificate(entry, False)
145  elif entry.enable_ssl:
146      ssl_ready = self._ensure_ssl_certificate(entry, True)
```

and line 182, `ssl=(entry.is_public or entry.enable_ssl) and ssl_ready`. The step-ca leaf is the
`elif` branch — it requires `nginx.webathome.org/enable-ssl: "yes"`, which
`app/annotations.py:145` defaults to `False` when the annotation is absent
(`parse_bool(annotations.get(ENABLE_SSL, None))`). With `ssl` false,
`app/template.j2` renders one `listen 80` server with the allow block and `proxy_pass`, and no
443 listener at all: plain HTTP, no certificate.

The plan's own cited exemplar carries the annotation the prose drops.
`/work/HelmCharts/charts/kubecoder/templates/controller-service.yaml`, cited at `plan.md:257` as
"the internal shape", is lines 10-13:

```
10    nginx.webathome.org/server-name: {{ .Values.service.controller.serverName }}
11    nginx.webathome.org/is-public: {{ .Values.service.controller.isPublic | quote }}
12    nginx.webathome.org/enable-ssl: "yes"
13    nginx.webathome.org/target-port: "8080"
```

with the chart default `isPublic: false` (`charts/kubecoder/values.yaml:544`) — i.e. the estate's
internal-TLS shape is `is-public: no` **plus** `enable-ssl: yes`, and `enable-ssl` appears nowhere
in `plan.md`. The ACME directory URL the plan attributes to the configurator is in fact the
certbot image's (`/work/DockerImages/certbot/app/certutils.py:11,36-38`, value from
`/work/HelmCharts/charts/nginx/values.yaml:10`), reached only once a certificate is actually
requested.

**Impact.** R5 requires exposure *"with homelab TLS"*. An executor following P1's bullet ships
argocd-server on plain HTTP. V10 is worded *"reachable behind the estate's exposure mechanism with
homelab TLS and is-public: no"*, so it reads as satisfied by exactly the annotation the plan names
— the failure is invisible to its own acceptance check, and lands on the operator at bootstrap.
V23 (SSO login, R18) rides the same vhost. P5's relay is unaffected: `is-public: "yes"` takes the
`if` branch and needs nothing extra, so the one Service the plan gets right is the public one.

---

## F3 — P1's homelab-CA guidance solves the ConfigMap half of a problem whose other half is in the subchart · advisory

**Problem.** P1 requires the repo-server to reach `https://charts.home` over the homelab CA (R14,
V19) and offers four patterns:

> Four existing patterns to choose from — a ConfigMap built by a deploy hook, a ConfigMap from
> chart `files/`, an init container rewriting a trust store, or baking into an image — and the
> chart-`files/` mount in `/work/HelmCharts/charts/nginx/templates/nginx-configmap-ca.yaml:1-6` is
> the closest fit. — `plan.md:262-267`

All four are patterns for a chart that templates its own pod. The repo-server is not the wrapper
chart's pod — it comes from the upstream `argo-cd` subchart that `Chart.yaml` `dependencies:` pins
(P1's own first paragraph). The cited exemplar is a six-line ConfigMap
(`apiVersion: v1 / kind: ConfigMap / metadata.name: nginx-configmap-ca / data: {{ (.Files.Glob
"files/ca/**").AsConfig }}`) and nothing else; it produces the object but carries no statement
about how it reaches a pod the chart does not own. "Baking into an image" is not available at all
against an upstream image.

**Impact.** The phase's stated success condition is `helm template` rendering a complete install,
which a ConfigMap alone satisfies — so P1 can land green with the trust half unwired, and R14 then
fails at bootstrap, in front of the operator, rather than in a phase. The plan derives no
expectation for whether `helm dependency build` (a subprocess of the repo-server, not Argo's own
HTTP client) consults a mounted trust store at all, which is the question R14 exists to answer.
D17's plain-HTTP fallback bounds the damage.

---

## F4 — the bootstrap ordering bullet contradicts P6's placement · nit

`plan.md:209-211` describes the bootstrap as *"one operator keystroke sequence … clone,
`helm dependency build`, `helm install`, **then the registry entry**"*, while P6
(`plan.md:391-411`) lands `configs/prd/argocd/prd/release.yaml` as a committed code phase — the
last one, before the operator installs anything. Two actors, opposite order, same artefact. Either
sequence produces the same end state (nothing serves the entry until the ApplicationSets exist, as
P6 itself says), so this is wording, not mechanism — but a reader reconciling R6 against the phase
queue has to notice the plan means P6.

---

## Out of scope for this review

Two observations already carried in the slice's own `close-out.md` — B2 (`slice.md`'s
ApplicationSet quote drops `hook.namespace`) and S1 (the register's "~44" is 15) — I independently
confirmed and have nothing to add. The `openbao.yml:91-96` citation in `plan.md:304-305` and V29
points at comment prose rather than the `openbao_eso_kv_paths` grant six lines below at 101-107;
the substance (the `eso/prd/*` trailing-glob covers `kv/eso/prd/argocd/prd/*`) is correct, and the
off-by-ten is inherited verbatim from slice 007's `credential-inventory.md`, so it is that file's
to fix, not this plan's.
