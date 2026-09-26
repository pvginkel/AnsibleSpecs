# Triage 2026-09-26 — raw material

Scope, set by the operator: DI-8 and ANS-125, as one slice, Ansible-led ("Can you pick up DI-8
together with ANS-125", then "Go" to the proposal quoted under Chat below); all DockerImages matrix
images in scope; upstream-image digest pins to a separate card. No other intake cards are in this
run. DI-8 is a DockerImages (`DI`) card; DockerImages has no spec repo of its own and its specs
live in AnsibleSpecs. Fetched 2026-09-25 with `get_issues` (comments included).

Everything below is verbatim from the tracker, with one mechanical rule: heading lines inside a
card's own text carry two extra `#` (ANS-125's five `##` headings are `####` here).

## DI-8 — registry-cleanup must never delete an image a deploy repo pins (GC --delete-untagged, keep-newest cap)

- Reporter: jeeves
- Created: 2026-09-25
- Updated: 2026-09-25
- State: New · Type: Task · Tags: none
- Parent: EPIC-5 (DHCPOutage)
- Relates: ANS-125, DI-5

### Description

On 2026-09-25 the nightly GC deleted `keycloak@sha256:fa01e691…`. The GC is `registry garbage-collect --delete-untagged`, hardcoded in `registry-cleanup/app/main.py`. KeycloakDeploy still pinned that digest after #2548 rebuilt the tag. After a power cut, Keycloak could not pull its image and took DHCP down with it.

Two rules delete deployed images:
- **GC `--delete-untagged`** removes a pinned digest as soon as its tag moves.
- **The keep-newest-10 cap ignores deploy pins.** `webhook-relay:2485` (argocd-prd), `dhcpapp-ui:45` and `electronics-inventory-ui:251` were 5–6 builds from deletion.

**The job is paused; lifting the pause is part of this card.** The 2026-09-25 stop-gap sets `suspend: true` in RegistryDeploy `chart/templates/registry-cleanup-cronjob.yaml`. Remove that line, and with it the comment, once cleanup reads the in-use set (deploy-repo pins, running pods and ReplicaSets) and fails closed when it can't read it. ANS-125 (tags vs. digests) settles part of the answer. This is DI-5's open question, now urgent. While paused, the registry only grows; keep an eye on its storage.

### Comments

None.

## ANS-125 — Image pins by digest: how the deploy repos came to carry hashes, and the operator's ask to reconsider

- Reporter: jeeves
- Created: 2026-09-25
- Updated: 2026-09-25
- State: New · Type: Task · Tags: none
- Parent: EPIC-5 (DHCPOutage)
- Relates: DI-5, DI-8

### Description

#### The ask (operator, 2026-09-25)

> I didn't realize DockerImages is writing hashes. I really don't like that. I would like a card explaining how this came to be and an ask by me to reconsider this.

#### How it came to be

DockerImages itself writes tags, not hashes. The hash that broke Keycloak came from HelmCharts, by way of the Argo CD migration:

1. **HelmCharts' deploy CLI has resolved every image to a digest at deploy time since 2024-08.** `tools/chart_tools/resolve_helm_args.py` calls `get_digest` and passes `--set images.<x>=@sha256:…`. A release therefore never ran a tag, so a rebuilt tag could not change a running release underneath it. Every deploy re-resolved, so a stale digest never lasted.
2. **The Argo CD bulk migration (D51, 2026-09-23/24) froze those digests into the deploy repos.** `support/argo-migrate/argo_migrate.py` `compose_values` copied `helm get values` into each `config/<stage>/values.yaml`, so the first Argo render would match the running release. It labelled them "each image at the digest the release runs (argo-cd D53)".
3. **D53 made builds the pin writers, and they write tags.** DockerImages' "Write image pins" stage writes the build number (`:<build>`), and app builds do the same through `cicd.writeVersionPins`. Wherever a build ran after the migration, the digest was replaced by a tag.
4. **Matrix images are skipped** (`if (!isMatrix) builtImages << image` in DockerImages' Jenkinsfile). Keycloak is a matrix image with a named, mutable tag (`26.7.3-postgres-health-ispn`), so its migrated digest was never replaced, even though `keycloak/deploy-pins.json` lists both KeycloakDeploy stages. On 2026-09-25 it was the only digest pin in any live workload.
5. **registry-cleanup still assumes HelmCharts re-resolves at deploy time.** Its GC runs `--delete-untagged`. DockerImages #2548 rebuilt keycloak onto the same tag (09-24 19:12Z), the pinned digest `fa01e691` went untagged, and the GC deleted it (09-25 01:32Z). The pod kept running from the node's cache until the power cut forced a pull, which failed. Keycloak down then took DHCP down.

#### To reconsider

- **Tags everywhere, digests nowhere?** This only holds if tags are immutable. A matrix image rebuilt onto `26.7.3-postgres-health-ispn` changes what a tag pin runs on the next pull, because the pods use `imagePullPolicy: Always`.
- **What a matrix image's pin should be.** For example, a per-build tag next to the named one (`26.7.3-postgres-health-ispn-<build>`), written by the pin stage like every other image's.
- **The migrated comment.** The comment the migration left in every deploy repo ("each image at the digest the release runs") is wrong wherever a tag is pinned.
- **D53's text** in AnsibleSpecs `argo-cd/decisions.md`. The cleanup side is DI-5 and DI-8.

#### The paused cleanup job

The 2026-09-25 stop-gap pauses registry-cleanup with `suspend: true` in RegistryDeploy `chart/templates/registry-cleanup-cronjob.yaml`, so no image is deleted until this is settled. **The pause must be lifted again.** That is DI-8's to do, once cleanup can no longer delete a pinned image. This card decides half of that: with immutable per-build tags and no digest pins, `--delete-untagged` can no longer orphan a pin, but the keep-newest cap still has to respect deploy pins (DI-8). Don't close this card or DI-8 with the CronJob still suspended and no ruling on who lifts the pause.

#### Current state

KeycloakDeploy pins `@sha256:45ae4959…` for both stages (075184c, the 2026-09-25 fix), which is the current digest of `26.7.3-postgres-health-ispn`. Its `rebuild-at` is 2026-10-01. The next keycloak rebuild orphans that digest the same way, and only the paused cleanup keeps it from being deleted.

### Comments

None.

## Chat, 2026-09-25/26 (verbatim, in order)

### Operator

> Can you pick up DI-8 together with ANS-125.

### Session (Claude), after reading both cards, the outage handover, registry-cleanup and the live Argo CD Application image lists

> DI-8 and ANS-125 together are big enough to need a slice. The work touches the registry-cleanup code and its cluster permissions, the DockerImages pin stage, KubeCoder's and Keycloak's deploy repos, and the decision text, so I'd run it as one Ansible-led slice through `/dev:triage` and then `/dev:plan-slice`. I haven't started either; they're your steps.
>
> There's no rush. The cleanup job is still paused, and while it is, nothing gets deleted, including Keycloak's image when it's next rebuilt on 10-01.
>
> **What I recommend for ANS-125: pin tags only, never digests.**
> - **Why it's safe:** every image from our registry would be pinned to a build-number tag. A build-number tag is never rebuilt, so it always points at the same image.
> - **What that asks for:** the only exception today is Keycloak. It's the one "matrix" image (built from a list of versions, with only a named tag) that a deploy repo pins, and it's the only workload running an image by digest. The other digest references still in the cluster come from old, finished job pods.
> - **The fix:** give Keycloak a per-build tag (`26.7.3-postgres-health-ispn-<build>`), and have the pin stage stop skipping matrix images.
> - **Also part of it:** correct the "digest the release runs" comment that the migration left in every deploy repo, and amend D53.
>
> **What DI-8 becomes after that:**
> - **Cleanup reads what the cluster runs** before it deletes anything: running pods, plus the image in every Deployment, ReplicaSet, StatefulSet, DaemonSet and CronJob. It protects all of those images.
> - **It fails closed:** if it can't read the cluster, it deletes nothing.
> - **The nightly clean-up of untagged images stays, with a guard.** If any image is still referenced by a digest that no tag points at, cleanup skips that step. Keycloak's image was deleted because this step removes images whose tag has moved.
> - **Then the pause is lifted.** The in-use set comes from the cluster, not from reading the deploy repos, which is the approach you rejected on 2026-08-16.
>
> **Two scope questions:**
> 1. **Outside images are also pinned by digest.** About 17 references across roughly 13 apps (nginx, jenkins, elastic, plex, gluetun and others) carry a bare digest that the migration froze in place. This isn't a deletion risk, because those images don't live in our registry. But they're the same kind of hash you dislike, and they never update: NginxDeploy's `nginx: :mainline` default is now overridden and does nothing. I'd give these their own card, because they need a policy for who bumps outside versions.
> 2. **KubeCoderDeploy runs `kube-coder-tunnel-reclaim:latest`,** a moving tag that nothing pins. It's small, so I'd fold it into this slice.
>
> If you agree with the recommendation, say go and I'll run `/dev:triage` on both cards as one slice, with outside images as a separate card.

### Operator

> Arguably all matrix builds get this behavior. Which ones are there?

### Session (Claude)

> There are eight matrix images. Keycloak is the only one a deploy repo pins; the other seven are pulled by their moving named tag.
>
> | Image | Named tag | Pulled by |
> |---|---|---|
> | `keycloak` | `26.7.3-postgres-health-ispn` | KeycloakDeploy, both stages (pinned by digest today) |
> | `k8s` | `1.35.5` | The shared Jenkins library's `k8s` container, which re-pulls on every run (live on a Jenkins agent now) |
> | `kube-coder-frontend-toolchain` | `node-24` | KubeCoder environments (2 running); also the base image of modern-app-toolchain |
> | `kube-coder-modern-app-toolchain` | `node-24` | KubeCoder environments (2 running) |
> | `kube-coder-java-toolchain` | `jdk-21` | KubeCoder environments (1 running) |
> | `kube-coder-esp-idf-toolchain` | `idf-5.5.3` | KubeCoder toolchain (none running now) |
> | `modern-app-dev-playwright` | `playwright-1.60.0` | App Jenkinsfiles, which work out the tag from the Playwright version in their lockfile |
> | `ubuntu-full` | `25.10` | The base image of `kube-coder-dev-base`; the version-poller has stopped rebuilding it (DI-5) |
>
> I agree it should be the same rule for all of them. Every matrix build would push `<tag>-<build>` next to the named tag, and the pin stage would write the per-build tag wherever a `deploy-pins.json` exists, which today is only Keycloak. The other seven keep pulling their named tag. That's what they want: a new KubeCoder environment or Jenkins run should get the latest toolchain build.
>
> **Something I noticed while checking:** registry-cleanup counts any tag ending in a dash and a number as an old build number. So it treats `node-24` and `jdk-21` as build 24 and build 21, not as named tags. That means cleanup could delete them once they're 26 weeks old without a rebuild. They survive only because cleanup always keeps a repo's newest tag. They're rebuilt often enough that it hasn't happened. The per-build tags will need clear rules in cleanup anyway, so I'd put this in the same slice.
>
> If you're happy with that, I'll run `/dev:triage` with all matrix images in scope.

### Operator

> Go

## Session evidence behind the chat (read live 2026-09-25, for the record)

- `kubectl get applications -A` `status.summary.images`: in-registry digest references were
  keycloak (both stages, `@sha256:45ae4959…`) and, from Succeeded job pods only, `git-sync`,
  `registry-cleanup`, `rclone-backup`, `version-poller`, `elasticsearch-setup`.
  `kubecoder-dev`/`kubecoder-prd` run `registry:5000/kube-coder-tunnel-reclaim:latest`.
- Upstream images pinned by bare digest (Application summaries): elasticsearch, kibana, filebeat,
  gitblit, nginx (git-sync, jenkins, models, nginx, trello-mcp), guacamole, guacd, jenkins,
  busybox, pms-docker, gluetun, text-embeddings-inference, pgadmin4, ha-mcp, registry.
  NginxDeploy `chart/values.yaml` `images.nginx: :mainline`; `config/prd/values.yaml`
  `images.nginx: '@sha256:abe47724…'` under the comment "Passed by HelmCharts' deploy CLI on top
  of the file, now pinned here: the stage name, and each image at the digest the release runs
  (argo-cd D53)."
- DockerImages matrix images (`*/build-matrix.json`): k8s, keycloak, kube-coder-esp-idf-toolchain,
  kube-coder-frontend-toolchain, kube-coder-java-toolchain, kube-coder-modern-app-toolchain,
  modern-app-dev-playwright, ubuntu-full. Only keycloak has a `deploy-pins.json`.
- registry-cleanup `_VERSIONED = re.compile(r"^(?:\d+|.+-\d+)$")` (`registry-cleanup/app/main.py`).
