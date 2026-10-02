# P3 code review, round 1: modernApp.test, the Modern app build type, SEC-1's exception

Range: JenkinsPipelineUtils `47cff67..02989a1` (`phase/036-P3`, one commit).

**Readiness: one blocking finding; otherwise ready.** I compared `vars/modernApp.groovy` with the
validation blocks of all five live app files (`/work/scratch/<App>/Jenkinsfile`). The five differ
only in the Job name, install/run commands, services and env. All of that is expressible, and
`jobManifest` renders it field for field as before: the toleration, resources, deadline, TTL,
uid, the emptyDir at `/work` and the suite script. The summary, description, archive, JUnit,
exit-code errors and the `finally` delete keep the old block's text. The Job's image is read from
`podYaml.sidecars()['modern-app-toolchain']` (`:47`), so it is declared once. No secret value
enters Groovy: `secrets` is names only, checked against a name pattern (`:259-264`).
`ModernAppTest` pins the manifest by JSON equality and covers every refusal. The guide follows
Ruling D1 and P3: the type page, the reference file from ElectronicsInventory (same images, tags
and pins as the live file), the index row, the J15 row, SEC-1's single exception and the
validation-Job "No helper" bullet. Its rule citations (LIB-1/3/6, POD-3, GRAN-2/3/4) say what
they are cited for. I ran the docs lint against the controller, and every example passed,
`modern-app.groovy` included. The defect is in the one new mechanism the unit harness cannot
reach: the shell handoff of `secrets` into the Job.

## F1 — Major · blocking · anchor: repro-trace · confidence: high (mechanism), the current secret's content unknown

**The `secrets` handoff silently corrupts any value that contains `#` or a newline.**
`vars/modernApp.groovy:71-73` sends each secret to `kubectl set env -e -` as a `NAME=value` line.
kubectl's stdin env reader treats `#` as the start of a comment, drops the rest of the line, and
reads each line as a separate variable. Nothing fails. The suite's container just gets a different
value, or an extra variable.

Witnessed with kubectl v1.35.9, the version the plan record cites. The `k8s` sidecar is
`alpine/k8s:1.35.5`, per `DockerImages/k8s/Dockerfile`. The pipe is the step's own:

- `KEYCLOAK_ADMIN_CLIENT_SECRET='ab#cd ef"g:h'` → the Job's `validation` container gets
  `KEYCLOAK_ADMIN_CLIENT_SECRET=ab`.
- `A=$'line1\nline2=oops'` → the container gets `A=line1` and also a variable `line2=oops`.

The step's page promises the full value: `vars/modernApp.md:85` says "Variables of the build's
environment that the suite gets under the same name", and `:114-117` says the step adds each one
"from a shell". The plan's P3 Record says the channel was "verified locally … with a value holding
quotes, spaces and colons". `#` and line breaks were not tested, and they are ordinary characters
in a secret.

When it happens, the suite fails on authentication or misbehaves. The real value never appears in
the log (`set +x`, withVault masking), so nothing in the build points to the truncation. Today's
one caller is IoTSupport's Keycloak admin client. Its secret was created in Keycloak by hand
(`IoTSupport/backend/README.md:73`), so it is most likely Keycloak's alphanumeric default, but I
cannot see it. The risk is a rotation to a value with `#`, or the next app that passes a password
through `secrets`. This is the one path the unit harness cannot run, and the defect above got
through the manual check that stood in for a test.
