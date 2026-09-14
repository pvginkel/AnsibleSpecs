# P5 code review — round 1

**Range:** `d393616a..cd2f50d` (branch `phase/019-P5`). **Gate:** green on `cd2f50d` (input, not re-run).

**Readiness.** Ready to merge. `docs/runbooks/internal-tls-expiry.md` delivers the phase outcome and V14–V16:
- **Order.** Step 1 checks SSH reachability and routes `Certificate invalid: expired` to `ssh-host-cert-expiry.md`. The runbook names the symptom for each of the three consumers and the Friday job behind a lapse. Step 3 gives `renew-internal-tls.yml` as the recovery. The OpenBao listener case has its own hand-run section, and `openbao.md`'s Consumer cold-boot intro, which names "listener cert expired", now links to the runbook.
- **Claims checked against the repo, no mismatch found:**
  - the leaf paths, SNI names and handler names (`roles/{proxmox_host,openbao,microk8s}/tasks/internal_tls.yml`, `group_vars/k8s_{prd,dev}.yml`, `host_vars/srvk8s4.yml`);
  - the task and `--check` report names (`roles/internal_tls/tasks/issue.yml:88-98,171`), and the kubelite failure text (`roles/microk8s/handlers/main.yml:124`);
  - both build descriptions (`Jenkinsfile.iac-scheduled-certs:78-95,150-156`) and the 7-day drift threshold (`Jenkinsfile.iac-scheduled-drift:50`);
  - the 47-day claims (`step-ca-bootstrap.md:121-127`);
  - step-ca needing nothing from OpenBao (`decisions.md:111`), and no OpenBao lookup anywhere on the renewal path. No role on it declares meta dependencies.
- **The OpenBao hand run.** The `iac-impl` login failure text and the rule that the resolver runs only when a `!bao` ref is left match `support/iac-agent/bin/iac-impl:90-91,160-170,462`. The SSH key's `!bao` ref and the literal vault passphrase match `secrets.example.yaml:179-189`. The KubeCoder key paths match `scripts/kubecoder-keys.sh:81-82` and `.kubecoder/config.yaml:66-67`, and the `sudo iac -c` shape and steps 1–5 match `iac-cold-boot.md`.
- **The markdown anchor** resolves to its heading.

Two minor wording defects remain, both advisory.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high
**The header's "prefix each command with `cexec iac`" gives a broken command for the runbook's own `cd ansible && poetry run …` lines.**

`docs/runbooks/internal-tls-expiry.md:6` tells a KubeCoder operator to prefix each command with `cexec iac`. The commands at :49 and :85 start `cd ansible && poetry run …`. Prefixed literally, that becomes `cexec iac cd ansible && poetry run …`, so `poetry` runs in the dev container, where it is not installed (`command -v poetry` finds nothing there). The working shape is `cd ansible && cexec iac poetry run …` (`docs/live-infra-access.md:64-66`), and the runbook's own KubeCoder block uses it at :151. Taken literally, the header fails at once with "command not found", so no harm follows, but step 1 and step 3 cannot be copied from it as written.

### F2 — Minor · advisory · anchor: none · confidence: high
**Step 1 says a timeout on srvk8sdev "only means it is off", which is not true from a KubeCoder environment.**

`docs/runbooks/internal-tls-expiry.md:56` reads a failed connection to srvk8sdev as the box being powered off. `docs/live-infra-access.md:116-118` records that srvk8sdev answers on neither 22 nor 16443 from a KubeCoder pod, and a probe from this pod got `No route to host` on 22. The runbook's KubeCoder route (:141-155) is exactly the setting where that reading is wrong. There, a running srvk8sdev looks powered off, and its lapsed leaf cannot be renewed from that controller. Only the dev node is affected.
