# P3 code review — round 1

ArgoCDDeploy `fb35a6c..0bacce1` (`phase/031-P3`, one commit, not pushed; base is `origin/main`).

**Ready to merge.** The phase meets its outcome (plan § P3, Ruling D3):

- **The pin moved.** It is now at `relay.image: ':2539'` in `config/prd/values.yaml:319`. The chart default is empty (`chart/values.yaml:55-58`), and the template adds the value to `registry:5000/webhook-relay` behind a `required` guard (`chart/templates/webhook-relay.yaml:45`). The old chart-level comment is gone.
- **The render is neutral.** I rendered `helm template argocd-prd chart --values config/prd/values.yaml` at both the base and HEAD, and the two outputs are byte-identical (34,715 lines, `cmp` clean). Test phase step 2 can therefore expect argocd-prd to stay Synced.
- **The pin stage can write to it.** The phase's value has to work with the P6 entry the plan names (`relay.image`, default template `:{tag}`) and with `cicd.writeVersionPins`. I ported `applyPins` from `JenkinsPipelineUtils/vars/cicd.groovy` to Python and ran it on the new stage file. `relay.image` resolves to exactly one line (319). That line is single-quoted, and `replacePin` keeps the quoting style, so a build writes `':<n>'`. That value still passes the new `RELAY_PIN` check (`tests/render-chart.py:297`).
- **The new render checks work.** I tested `check_relay_pin` (`tests/render-chart.py:1381-1396`) with two mutations, and it caught both:
  - dropping `required` from the template fails with "chart/ renders a relay for a stage that pins no build…";
  - pinning `':latest'` in the stage file fails both the `RELAY_IMAGE` check and the `RELAY_PIN` check.
- **Nothing depends on the old chart default.** Every other stage fact in this chart is already `required`-guarded, and both lint and test render with `config/prd/values.yaml`. A search of Ansible, DockerImages, JenkinsPipelineUtils and ArgoCDTools found no other reader of `relay.image` or of the old literal. `docs/architecture/` is generated and untracked.

## Findings

None.
