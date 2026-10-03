# P5 code review — round 1

**Readiness: ready to merge.** The diff (`234f665`, DockerImages `phase/040-P5`) meets P5's outcome.
`elasticsearch-setup/app/main.py:66-82` creates user `reader` with the built-in `viewer` role.
On Elasticsearch 8.15, that role reads every index whose name has no leading dot, data streams
included. It logs into Kibana read-only and holds no cluster privilege, which is Ruling
review-Q1's shape. The setup job runs it after `create_logstash_internal_user` (`:150`).

The password comes from env `READER_PASSWORD` (`:11`), which is the environment-value route the
plan asks for. The name is recorded in the done-record for P6 and P7. `put_user` on an existing
user replaces its password and roles, so a rerun converges, and P6's rotation path depends on
that. The `architecture.yaml` summary change passes the gate's `arch-validate`.

I ran two targeted checks with the image's own client range (`elasticsearch>=8,<9`, which
resolved to 8.19.3):

- Against a local HTTP stub, `create_reader_user` sends exactly
  `PUT /_security/user/reader {"password":"…","roles":["viewer"],"full_name":"Read-only reader"}`.
  That is the 8.x security API shape.
- With the variable unset, `import main` raises `KeyError: 'READER_PASSWORD'`. The comment at
  `:9-10` says so, and the done-record's P6 hazard depends on it.

The other two checks:

- **Hazard across phases.** A pin of this image that lands before P6's wiring fails the job at
  start. The done-record says so and the plan's Ordering constraints cover it, so it is not a
  P5 defect.
- **Live witness.** The reader's limits are witnessed live in the test phase (Ruling D4, V09),
  not here.

## Findings

None.
