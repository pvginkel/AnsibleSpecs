---
issue: ANS-120
---

# Straightforward changes — triage 2026-09-24

Six clear, low-risk fixes from the 2026-09-24 triage of the ANS intake queue. The operator asked for
them to be "done without a slice", worked through in one conversation. Five had qualified for a
Solution Known sweep; this handover replaces that sweep. The triage record is AnsibleSpecs
`handovers/triage_2026-09-24.md` and `…_raw.md` at `1b6cd36`, and the source cards (ANS-111, ANS-114,
ANS-63, ANS-77, ANS-48, ANS-112) are closed as absorbed under ANS-120, which tracks this document.

The items are independent; any order works. Items 3 and 4 both change ArgoCDDeploy and can share one
push. Item 2 applies to every ArgoCDDeploy push, these two included: `argocd-prd` does not refresh on a
push, so refresh it by hand.

Pushes, and the Argo syncs a push to a deploy repo's `main` sets off, are the operator's call. Ask
before each push.

## 1. `architecture-viewer` and `webathome-org` roll out without a gap (ANS-111)

**Source.**

- ANS-111: "Find out why architecture.webathome.org is unavailable as often as the reports show, and
  fix that rather than the lint gate that notices it. Whether nginx and webathome.org are deployed in
  an HA manner is part of the question." Operator ruling: "Agree".
- Triage research (2026-09-24, posted on ANS-111): the outages are `architecture-viewer` rollouts. The
  dataset is baked into its image. `AaC/Architecture` runs downstream of all 79 registered producers,
  and each run builds a new image and pins it into WebathomeOrgDeploy, where Argo auto-syncs it. With
  `replicas: 1` and `strategy: Recreate`, each publish leaves about 35–45 s with no pod: a rollout every
  5–9 minutes, 195 pin commits on 2026-09-24.
- Operator, in chat: "e.g. ANS-111; I mean, that's a one word change, right?"

**Grounding (WebathomeOrgDeploy `fc256e3`, read 2026-09-24).**

- `chart/templates/architecture-viewer-deployment.yaml`: `replicas: 1`, `strategy: type: Recreate`,
  no volumes. It has a readiness probe (`httpGet /healthz :8080`, `initialDelaySeconds: 2`,
  `periodSeconds: 5`) and a liveness probe.
- `chart/templates/webathome-org-deployment.yaml`: `replicas: 1`, `strategy: type: Recreate`, no
  volumes, no probes, container port 80.
- The pod-template annotation `deployment.timestamp` is fixed (`_helpers.tpl`), so it rolls nothing.

**Change (WebathomeOrgDeploy).**

- Both Deployments: `strategy.type: RollingUpdate`. At one replica the defaults (25%/25%) surge one
  new pod and keep the old one until the new one is Ready.
- `webathome-org`: add a readiness probe on port 80, so the old pod is kept until the new one serves.
  The path is yours to confirm; `/` is the likely one.
- Run the repo's `kc project test`.
- WebathomeOrgDeploy gets a pin commit every few minutes, so pull with `--rebase` just before pushing.

**Done when.**

- During the next architecture publish, the old `architecture-viewer` pod is deleted only after the
  new one is Ready (`kubectl get events -n webathome-org-prd`, `kubectl get rs -n webathome-org-prd`).
  `arch-validate` run across a publish gets no 5xx.
- The next `webathome-org` rollout shows the same overlap.

**Operator stops.** The push, which Argo auto-syncs to prd.

**Not in this item.** You have not ruled on either of these; each needs a new card if it is still
wanted:

- A node drain still takes each single pod down. Covering that needs 2 replicas and a
  PodDisruptionBudget.
- Every publish still rebuilds the image and commits a pin.

## 2. The Argo CD upgrade runbook refreshes `argocd-prd` by hand (ANS-114)

**Source.** ANS-114: "ArgoCDDeploy's docs/runbooks/argocd.md ("Upgrading Argo CD", step 2) says a
push to ArgoCDDeploy refreshes the `argocd-prd` Application through the webhook, but ArgoCDDeploy has
no webhook (no terraform/, unlike the migrated apps' deploy repos). After a push on 2026-09-23,
`.status.sync.revision` still showed the old commit 5 minutes later." — "Asked: change step 2 to
refresh by hand after the push, `kubectl annotate application -n argocd-prd argocd-prd
argocd.argoproj.io/refresh=normal --overwrite` with the prd write kubeconfig, which showed the new
revision within seconds." Operator ruling: "Agree".

**Grounding.** The section is in *this* repo, not ArgoCDDeploy: Ansible `docs/runbooks/argocd.md`,
"## Upgrading Argo CD" (line 181). Step 2 reads "The webhook refreshes `argocd-prd`; it goes
OutOfSync."

**Change (Ansible).** Step 2 refreshes by hand after the push, with the card's command and the prd
write kubeconfig. The webhook claim is gone. The card's "A webhook for ArgoCDDeploy only if its pushes
are frequent enough to matter" is not part of this item.

**Done when.** Step 2 gives the refresh command and no longer says a webhook refreshes `argocd-prd`.

## 3. The PreSync hook environment carries `HOMELAB_S3_BACKUP_READER` (ANS-63)

**Source.** ANS-63: "P4 added HOMELAB_S3_BACKUP_READER: backup-reader to HelmCharts
_providers/clusters.yaml prd.env. ArgoCDDeploy config/prd/values.yaml hooks.environment.literals says
it copies that env verbatim, because the hook runs Terraform without the deploy CLI. It has no such
key, and tests/render-chart.py HOOK_ENV_LITERALS pins only four fixed keys, so its gate does not
notice." — "The fix is one literal in values.yaml plus the key in HOOK_ENV_LITERALS". Consequence
(card): "After an S3 release migrates to Argo CD, a prd bucket it adds is never granted to
backup-reader, so every mirror run fails on that bucket and S3MirrorStale fires two days later."
Operator, asked whether an S3 release had migrated: "Yes. All apps have been migrated." The gap is
live.

**Change (ArgoCDDeploy).** `config/prd/values.yaml`, `hooks.environment.literals`: add
`HOMELAB_S3_BACKUP_READER: backup-reader`. `tests/render-chart.py`: add the key to
`HOOK_ENV_LITERALS`.

**Done when.** The render test pins the key, and the rendered hook environment carries it.

**Operator stops.** The push, then a hand refresh of `argocd-prd` (item 2). On the next sync of an app
whose Terraform calls `s3-storage`, check its PreSync log: a bucket added since the app migrated now
gets its backup-reader grant, and that is the only change expected.

## 4. The webhook relay moves to `RECEIVERS` with its image pin (ANS-77)

**Source.** ANS-77: "`chart/values.yaml` pins `registry:5000/webhook-relay:2485`, which predates it,
so nothing is broken today. Migrate with the pin, in one commit:" the image to "`2530` or later"; "the
two env vars become one `RECEIVERS`, `argocd-server=<url>,applicationset-controller=<url>`, still
derived from the release's Service names rather than literal"; "`tests/render-chart.py`:
`RELAY_RECEIVERS` and the assertion that pins the whole of the relay's environment follow." The rules
are in DockerImages `webhook-relay/README.md`. Operator ruling: "You can move the pin. It's fine to
use the current version."

**Change (ArgoCDDeploy), one commit.** `chart/values.yaml` pins `relay.image` to the current
`webhook-relay` build. `chart/templates/webhook-relay.yaml` replaces the two env vars with
`RECEIVERS`. `tests/render-chart.py` follows.

**Done when.** The render test is green. After the sync, a push to a migrated app's deploy repo still
refreshes its Application, and the relay logs both legs accepted.

**Operator stops.** The push and a hand refresh of `argocd-prd`; this can share a push with item 3.

## 5. The registry gate checks upstream-chart entries' keys (ANS-48)

**Source.** ANS-48: "HelmCharts `tests/test_prd_tree.py:93-113` asserts only the local-chart keys
(`deployed`, `autoSync`, `repo`, `targetRevision`, no `chart`) on every `reconciler: argo-cd` entry.
The upstream ApplicationSet (ArgoCDDeploy `chart/templates/applicationsets.yaml:148-166`) is selected
by `upstream.chart` and resolves `upstream.repo` / `.chart` / `.version` under `missingkey=error` — an
entry missing one passes the gate, then breaks generation for every upstream-chart Application at
once." Triage research (2026-09-24, HelmCharts `3c7524b`): nine `reconciler: argo-cd` entries carry
`upstream:` (ceph-csi-cephfs, ceph-csi-rbd, cloudnative-pg, csi-driver-smb, external-secrets, grafana,
headlamp, prometheus, step-ca), and the test never mentions `upstream`. Operator: "Yes, all apps have
been migrated."

**Change (HelmCharts).** In `tests/test_prd_tree.py`, an Argo entry with an `upstream:` block must
carry non-empty `upstream.repo`, `upstream.chart` and `upstream.version`. Slice 029 moves the registry
and its tests out of HelmCharts, and this assertion goes with them.

**Done when.** The test fails an upstream entry that lacks any of the three keys, and passes on the
current tree's nine.

## 6. YouTrack's backup opts into BackupOverdue (ANS-112)

**Source.** ANS-112: "does opting YouTrack in (valid_for=52h in its upload, then deleting the
youtrack-backup rule group and tests/test_prometheus_youtrack_backup_alert.py) belong in this slice,
or in a follow-up card?" Consequence (card): "The YouTrack backup is never a watched backup-server
stream, and the interim CronJob-status rule stays although its own comment says slice 023 retires
it." Its 2026-09-24 comment: the uploader is `YoutrackDeploy/chart/files/backup/backup.py`, the rule
group is in `PrometheusDeploy/config/prd/values.yaml` (~210-236), and the alert test is already gone.
Operator ruling: "Yes, include."

**Grounding.** YoutrackDeploy `chart/files/backup/backup.py:105` posts `/upload?filename=…` with no
`valid_for`. The precedent is PostgresPasDeploy `chart/templates/backup-configmap.yaml`: `VALID_FOR =
"52h"`, sent as `urllib.parse.urlencode({"filename": filename, "valid_for": VALID_FOR})`.

**Change, in order.**

1. YoutrackDeploy: the upload declares `valid_for=52h`, as postgres-pas's does.
2. **Stop**: wait until a nightly YouTrack upload carrying the validity has landed and BackupOverdue
   watches the `youtrack` scope.
3. PrometheusDeploy: delete the interim `youtrack-backup` rule group, and its "goes once slice 023
   ships" comment with it.
4. Docs: the "Streams watched today" table in Ansible `docs/runbooks/backup-freshness.md`, and
   AnsibleSpecs `decisions.md` §Backup's YouTrack entry (line 616, which today says "Its uploads
   declare no validity, so `BackupOverdue` does not watch it; `YouTrackBackupStale` fires critical
   after 52 h without a successful run of the CronJob").

**Done when.** BackupOverdue covers `youtrack`, the interim group is gone, and both documents describe
YouTrack as a watched stream.

**Operator stops.** The YoutrackDeploy push, the wait in step 2, and the PrometheusDeploy push.
