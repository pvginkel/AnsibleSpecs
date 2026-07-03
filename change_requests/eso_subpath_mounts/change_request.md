# ESO secrets on subPath mounts — pgadmin, media/mydownloads, elasticsearch/kibana

**One line:** Three charts still mount rotating ESO Secrets via `subPath` — the pattern
that permanently wedges a pod after secret rotation — and each needs a chart-specific
remediation because the target directories are image-owned.

Triage source: Triage cards **#54**, **#55**, **#56** (HelmCharts label; folded into this
bundle). Root cause and prior art are established.

## Root cause (shared by all three)

A Secret mounted via `subPath` caches the source inode at pod-creation and never rebuilds
it on container restart. When ESO rotates the secret, the next container restart fails to
mount with "not a directory" → permanent CrashLoopBackOff. Already fixed by switching to a
projected volume in: calendar-support, phpmyadmin, version-poller. The remaining three are
harder because each injects files into a directory the image (or a PVC) owns, so the
blanket projected-volume fix doesn't transplant.

## Card #54 — pgadmin

`charts/pgadmin/templates/pgadmin-deployment.yaml`: `pgpass` volume → secret
(`externalSecrets.secrets.pgpass`), subPath `pgpass` at `/pgadmin4/pgpass` (plus a
`servers.json` configMap subPath into the same dir — lower risk, same dir-ownership
constraint). `/pgadmin4` is image-owned. Candidate remediation: mount the secret at a
sibling dir (e.g. `/pgadmin4-secrets`) and point pgadmin's config at it, or an
initContainer copy into an emptyDir. First confirm whether the pgpass secret actually
rotates — pgadmin's DB password file plausibly does, so real risk, not theoretical.

## Card #55 — media/mydownloads

`charts/media/templates/mydownloads-deployment.yaml` — TWO secret subPaths:
`gluetun-config` → secret `gluetun-wg`, subPath `wg0.conf` at
`/gluetun/wireguard/wg0.conf`; `mydownloads-config` → secret `mydownloads-config`, subPath
`config.xml` at `/var/local/mydownloads/config.xml`. Both target dirs are image-/PVC-owned
(`/var/local/mydownloads` also holds the mydownloads-var PVC). Candidate remediation:
per-file — dedicated dir + symlink/config pointer, or initContainer copy. Confirm rotation
likelihood first: the gluetun wireguard key probably does NOT rotate (low priority);
mydownloads-config depends on what it holds.

## Card #56 — elasticsearch/kibana

`charts/elasticsearch/templates/kibana-deployment.yaml`: `config` volume → secret
`kibana-config`, subPath `kibana.yml` at `/usr/share/kibana/config/kibana.yml` —
image-owned dir with other config files. Candidate remediation: mount at a dedicated path
and set `KBN_PATH_CONF` / point kibana at it, or initContainer copy. Real risk if
kibana-config inlines the ES password (which rotates) — confirm before prioritising.

## Notes for the slice writer

- Per-chart "does this secret actually rotate?" is the first gate — it sets priority
  within the slice.
- The estate rule this enforces is already in operator feedback/memory: never mount a
  rotating Secret via subPath; use a projected volume (or the per-chart workaround where
  the dir is image-owned).
- Self-contained in HelmCharts (HelmCharts-tagged cards retained).
