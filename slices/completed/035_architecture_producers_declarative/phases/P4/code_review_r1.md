# P4 code review r1 — Ansible, DockerImages and IoTSupport producers

**Readiness: ready to merge, no findings.** The phase reaches its outcome. It is reviewed across
Ansible `9b257ce..5b4b984`, DockerImages `8cb59df` (`/work/DockerImages`) and IoTSupport `07401c8`
(`/work/scratch/IoTSupport`); each clone is one commit ahead of origin, and the scratch DockerImages
duplicate is untouched. All three files are full declarative files to the guide: header, library
line, one `pipeline {}` on `jenkins-agent` with `podYaml`, the reference `options{}` (with
`abortPrevious: true`) and `triggers{ githubPush() }`, and a `Checkout` stage running
`checkout scm`. Validation and archiving go through `architectureProducer`. I sent the three files
to the controller's linter myself, and each answered "Jenkinsfile successfully validated."
`GET …/config.xml` for AaC/Ansible, AaC/DockerImages and AaC/IoTSupport matches each header's
`Controller config:` block (`pvginkel/<Repo>`, `*/main`, `Jenkinsfile.architecture`), and none of
the jobs has a UI trigger the file leaves out. Each producer archives the same files as before:
Ansible's `docs/architecture/` holds only `ansible-architecture.yaml`. IoTSupport archives its
two backend models and `frontend/docs/architecture/*.yaml`, and `firmware-products.yaml`,
`SEED-NOTES.md` and the rest stay out. Every archive pattern passes the helper's `collected` check.
The phase's acceptance points hold:

- **R7 / V07.** Ansible runs on `jenkins-agent` without `kaniko` (`Jenkinsfile.architecture:16`).
- **J24 / V06.** DockerImages' hand clone is replaced by `checkout scm`.
- **S4 / V12.** IoTSupport's `withVault` wraps only the generator's `sh`, with `pip install`
  outside it, nested exactly like the guide's own SEC-1 recipe (`docs/examples/firmware.groovy`
  `deploy`). `$KEYCLOAK_OIDC_TOKEN_URL` stays as the recorded exception.
- **POD-4.** The python container (`[image: 'registry:5000/python', name: 'python']`) renders the
  same container as the retired `containerTemplates.python`: same image, `Always` pull,
  `sleep infinity`, no `runAsUser`.

None of the three files has trailing whitespace, and each ends in a newline. The deterministic
gate (root unit tests) is green and does not touch these files. The live builds are the test
phase's.

## Findings

None.
