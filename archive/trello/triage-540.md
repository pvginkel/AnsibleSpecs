# Bump the go toolchain sidecar to Go 1.26

## 📋 List: Operator Actions

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 150 (worker TUI -> Bubble Tea v2 + Lipgloss v2) needs Go >= 1.25; current stable is 1.26.5 (1.27 is still rc).

`kube-coder-go-toolchain/Dockerfile` installs Go from apt `golang-go`, which caps at `2:1.24~2` — apt cannot deliver 1.25 or 1.26 at all, so any bump means dropping the apt install. Suggested: `COPY --from=golang:1.26-bookworm /usr/local/go /usr/local/go` plus PATH, leaving golangci-lint, build-essential, pkg-config and tmux untouched.

Verify: `kaniko --context kube-coder-go-toolchain --no-push --timeout 0` from /work/DockerImages, then `cexec go go version` once the image is pushed and environments restart.

The KubeCoder-side pins ride slice 150, not this card: `worker/go.mod` and the Jenkinsfile agent image (`golang:1.24-bookworm` -> `golang:1.26-bookworm`).

Not blocking. GOTOOLCHAIN=auto already downloads a newer toolchain on demand (verified in the sidecar), so slice 150 gates green without this. Doing it first means the sidecar genuinely runs 1.26 instead of auto-switching per container.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/10/2026, 11:25:50 AM
Done and pushed: DockerImages 91f2121 on main (rebased over slice 139's base-image commits, which touch no file this one does).

Took the tarball instead of the suggested COPY --from=golang:1.26-bookworm. The golang image does nothing but untar that same archive into /usr/local, so the image pulls ~800MB for one directory, puts Docker Hub in the path of every rebuild, and pins a moving tag. Now: ARG GO_VERSION=1.26.5 / GO_ARCH / GO_SHA256, curl + sha256sum -c + tar -C /usr/local, matching how kube-coder-dev pins OpenBao. Build 80s -> 39s, and a substituted tarball fails the build. No /usr/local/bin symlinks: upstream ships none.

Verified by appending probe layers to the real Dockerfile (so the tested prefix cannot drift): go1.26.5, GOROOT derived from binary location, all ten toolchain binaries statically linked, pure-Go and cgo builds run as uid 1000, golangci-lint 2.12.2 type-checks the 1.26 stdlib, full `go build -a` stdlib rebuild from source. Jenkins dependency graph unchanged (parent kube-coder-dev-base, no descendants).

Left for you, as agreed: track the DockerImages build, restart environments, then `cexec go go version` should report go1.26.5. Note the base image also changed in slice 139, so this image rebuilds on the new base.

GOTOOLCHAIN stays `auto` (upstream's image pins it to `local`) -- a go.mod asking for newer still silently downloads rather than failing.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/5gquxta3/540-bump-the-go-toolchain-sidecar-to-go-126
- **Short URL**: https://trello.com/c/5gquxta3

---
*Last Activity: 8/10/2026, 11:53:09 AM*
*Card ID: 6a79b08be86bb4b26db86d62*
