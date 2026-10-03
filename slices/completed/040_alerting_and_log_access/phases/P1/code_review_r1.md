# Code review — slice 040, phase P1, round 1

Range `3c9ca32d..999f874` (branch `phase/040-P1`).

**Readiness: ready to merge.** The `dhcp_probe` role does what P1 asks for. srviac's play
(`ansible/playbooks/site.yml:42`) installs it as a 3-minute systemd timer. The timer sends a
relay-style DISCOVER (`hops=1`, giaddr = srviac's own address, sent from and answered on UDP 67)
to `10.2.1.10`. It matches the OFFER on xid + chaddr + op + message type over an unconnected
socket, so a reply that NAT has rewritten to a node address and port still matches, as the
attachment's wire requires. It writes `dhcp_probe_success`, `dhcp_probe_duration_seconds` and
`dhcp_probe_last_run_timestamp_seconds` (`{server="10.2.1.10"}`) to the textfile collector,
writing a temp file and renaming it.

Checks I ran:
- The service template rendered against the prd inventory gives `--giaddr 10.1.0.45`. The
  `network_devices` derivation is correct.
- `python3 -m unittest discover -s ansible/roles/dhcp_probe/tests` passes 11 tests. The gate log
  covers only `--project ansible` (yamllint, ansible-lint), so it did not run these unit tests.

Timing:
- `OnBootSec=1min` elapses at once when the timer is first started on a host that has been up
  longer than that, so the first result lands at apply time.
- The longest gap between results is 3 min + 10 s accuracy + 10 s timeout, which matches the
  cadence the done-record hands to P3.

The IP-instead-of-hostname exception carries its reason (`defaults/main.yml:2-4`). The
`daemon_reload` on the `systemd` task does not report `changed`, so a second run stays at
`changed=0`. One advisory finding.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high
**Check mode never reports the timer's enabled/started state.** The task at
`ansible/roles/dhcp_probe/tasks/main.yml:21-30` has `when: not ansible_check_mode`, so it is
skipped on every dry run, not only the first one, when the unit file does not exist yet.

- **First run:** `--check --diff` previews the three files but not the enable/start of
  `dhcp-probe.timer`. V14's "shows the first run's changes" is met only for the files.
- **Later runs:** on a converged host where the timer has been stopped or disabled, the dry run
  reports nothing, and the apply then reports `changed=1`.

This follows a repo precedent (`ansible/roles/microk8s/tasks/watchdog.yml:43-45`), and the
done-record states it. P3's staleness warning would raise a stopped timer in production. Recorded
once in the close-out report; it is not fix work.
