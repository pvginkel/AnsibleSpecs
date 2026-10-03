# P6 code review — round 1

Range `08b18ef..9b33665` on ElasticsearchDeploy `phase/040-P6`. Gate GREEN on `9b33665` (gate_r1.log), taken as given.

**Readiness: ready to merge; no findings.** The phase delivers its outcome. `READER_PASSWORD` reaches the setup Job only through `secretKeyRef` on Secret `elasticsearch-reader`. That Secret is materialised by a new `externalSecrets.secrets.reader` entry from `eso/prd/elasticsearch/prd/filebeat-reader`/`password` (`config/prd/values.yaml:14-19`; I rendered it to an ExternalSecret with `secretKey: "password"`, which matches the Job's `key: password`). The Job name now hashes the whole `elasticsearch-setup.spec` include (`chart/templates/elasticsearch-setup-job.yaml:27`) and none of the hook values, so it is stable across commits and moves with any spec change. That covers V11's "reruns on any spec change", and the inert `helm.sh/resource-policy` annotation is gone.

`tests/setup-job.sh` is not vacuous. I ran three mutations in a throwaway worktree and each one went red: naming the Job from the pin alone gave rc=1 ("did not change with its env"), a plain `value:` for READER_PASSWORD gave rc=4, and a wrong secret key gave rc=4.

**Push order.** P6 lands before CI's pin. The old image `:2565` (`put_role`/`put_user`, idempotent) then reruns harmlessly as `elasticsearch-setup-c47cc`. Live state is consistent with the done-record's sequence: the app syncs automatically with `prune: true, selfHeal: false`, the only Job is `elasticsearch-setup-14d87`, and ESO is v2.11.0.

**README rotation path (V16).** It accounts for both obstacles the plan names: ESO's hourly refresh (a `force-sync` annotation, then a wait on `status.refreshTime`, which reads live on the sibling ExternalSecret) and Argo CD not recreating a deleted Job (the operator starts a sync). The Job comes back under the same name because the password value is not part of the hashed spec.

**Rebase note.** `origin/main` has moved by `64d68bf`, which bumps homelab-shared to 0.4.0 in `chart/Chart.yaml` and `Chart.lock` only. It merges cleanly with this branch (`git merge-tree`).

## Findings

None.
