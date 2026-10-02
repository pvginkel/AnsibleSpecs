# P2 code review — round 1

**Range:** JenkinsDeploy `f3ee7df..80dc52a` on `phase/037-P2` (one file:
`chart/templates/destroy-stage-serviceaccount.yaml`). **Gate:** green on `80dc52a`
(`gate_r1.log`). Not re-run.

**Readiness: ready to merge.** The phase is meant to produce a ServiceAccount in `jenkins-prd`
that exists only for the Destroy Stage pipeline, holds no grant there, and leaves
`jenkins-prd/default` as it was. A comment should cite argo-cd D66 and say the grants are P3's. The
diff does all of that. A targeted `helm template` renders `ServiceAccount/destroy-stage` and
nothing else new. The chart adds no RoleBinding, and `jenkins-agent-jobs`
(`chart/templates/jenkins-agent-jobs-rolebinding.yaml:8-10`) still binds only `default`.

On live prd, I listed every ClusterRoleBinding and RoleBinding. Nothing reaches a `jenkins-prd`
ServiceAccount by group except the stock `system:serviceaccounts` /
`system:authenticated` discovery bindings (`system:service-account-issuer-discovery`,
`system:basic-user`, `system:discovery`, `system:public-info-viewer`). So the header's claim
"holds no grant in this namespace" is true. The header's other claims also match the record:

- D66 exists on AnsibleSpecs `main`, at `ffdaeeb`.
- D41's amendment (`argo-cd/decisions.md:875-883`) says, as the header does, that any pod in
  `jenkins-prd` may run as the ServiceAccount.

The header is a `{{/* */}}` Helm comment, so nothing of it renders. That follows
`chart/templates/namespace.yaml:1-5`. The header carries a reason and does not narrate history.
The one gap I found is that JenkinsDeploy's gate does not pin "no grant in `jenkins-prd`". Close-out
T1 already records that, so I raise no new finding for it.

## Findings

None.
