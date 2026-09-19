# nginx-configurator: the step-ca certificate only carries the first server name, so extra hostnames get a vhost with no matching SAN

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages
- `sky_dark` Project-ArgoCD

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

**Reported by the operator, 2026-09-04, standing Argo CD up.**

`nginx.webathome.org/server-name` on the `argocd-prd-server` Service was changed from `argocd.home` to `argocd.home, argocd` so the UI answers on the bare host as well, matching the shape the estate's other internal UIs already use (`headlamp.home, headlamp`, `grafana.home, grafana`, `prometheus.home, prometheus`).

`https://argocd.home` works. **`https://argocd` does not** — the certificate served carries only `argocd.home` as a SAN, not `argocd`. So the vhost exists for the extra name but the step-ca leaf was requested for the first name alone, and the browser rejects it.

Expected: every hostname enumerated in `server-name` ends up in the requested certificate's SANs, since `parse_server_names` already splits the annotation into a list and nginx serves all of them.

Scope note: the annotation is parsed as a list, so this presumably affects any Service enumerating more than one internal name with `enable-ssl: "yes"` — not just Argo CD. Whether the existing multi-name UIs are also affected has **not** been checked.

Not researched — filed on the operator's instruction to card the basics only.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/13/2026, 1:48:24 PM
**2026-09-13 — fix committed, not yet pushed/deployed** (DockerImages `e0a9944`, `bf81586`).

- nginx-configurator reads each cert's SANs and requests the cert again, with every name, when a name is missing. The existing cert stays in use until the new one arrives.
- certbot passes `--cert-name <first name> --renew-with-new-domains`, so a removed or replaced name updates `live/<first name>/` instead of starting an orphaned `-0001` cert.
- Hardening: rewrites run on one thread, each watch starts from a full service list, failed nginx restarts are retried, and invalid annotations keep the service's previous entry. The renewal job carries on past a failed cert and still fails at the end.

Before the fix went in, every live cert on prd was checked and covers all its names, so deploying it triggers no reissues.

### Jeeves (@jeevesginbov) - 9/13/2026, 1:35:31 PM
**2026-09-13 — closing: the symptom has resolved itself.** The live argocd.home cert now lists `DNS:argocd, DNS:argocd.home` (issued 2026-09-12 23:00 UTC). The other multi-name `enable-ssl` services (charts, homeapps, kubernetes, kubecoder, backup-server, tfmirror) were re-issued at the same time and also carry both names.

Cause, for next time: `nginx-configurator/app/nginxconfigurator.py` `_ensure_ssl_certificate` asks certbot for a cert only when `live/<first name>/fullchain.pem` is missing. It never checks which names that cert covers. So adding a name to an existing annotation does nothing until `nginxmanager-renewal-cronjob` runs (weekly, `0 1 * * 0`), which re-requests with every name. certbot's `--renew-by-default` then expands the existing cert.

Still possible, not fixed: an added name can be missing from the cert for up to a week. If a name is removed or replaced, certbot starts a new `<name>-0001` cert. nginx keeps reading the old one, which then stops being renewed and expires. A fix would be to compare the cert's names in the configurator and pass `--cert-name <first name>` in `certbot/app/certutils.py`.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/huN6MjvD/845-nginx-configurator-the-step-ca-certificate-only-carries-the-first-server-name-so-extra-hostnames-get-a-vhost-with-no-matching-sa
- **Short URL**: https://trello.com/c/huN6MjvD

---
*Last Activity: 9/13/2026, 1:48:24 PM*
*Card ID: 6a9b1a23599923b97806ec09*
