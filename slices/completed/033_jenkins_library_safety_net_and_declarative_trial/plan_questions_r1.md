# Slice 033 — plan questions, round 1

## Q1 — R1 asks for `when{}` and `post{}`, but KubeCoder's Jenkinsfile has nothing for either

**The decision.** R1 (the review plan's §3 wording, adopted as your step order) lists the
converted file's shape as "`agent { kubernetes { yaml … } }` built from a library
`containerTemplates.podYaml(...)`, `options{}`/`triggers{}` for its job config, `when{}`,
`post{}`". The scripted `KubeCoder/Jenkinsfile` has no conditional stage and no failure or cleanup
handling. Every stage runs on every build (`Jenkinsfile:31-340`: no `if`, `try`, `catch` or
`finally` outside comments). So nothing in the file maps onto `when{}` or `post{}`. The review
listed them as what declarative *buys* in general (report J08, "What it buys": "`when {}` instead
of `Utils.markStageSkippedForConditional` …; `post {}`"), not
as something this file needs. `verification.json` V01 carries R1 word for word, so as it stands
the trial cannot pass without one or the other. Rewording V01 needs your ruling.

**Options.**

- **A — Convert faithfully; the file gets neither.** Declarative constructs go only where the
  scripted logic has a counterpart. This file has none, so the trial shows `agent`, `options`,
  `triggers`, `stages` and `script {}`. V01 drops "`when{}`, `post{}`".
- **B — Add a real use of each so the trial shows them.** Any such use changes what the build
  does. There is no credible `when{}`: every image stage feeds the pin write, so skipping one
  would pin an image that was never built. The only candidate for `post{}` is a failure alert,
  and `jenkins-telegram-bot` already reports FAILURE loudly by itself
  (`JenkinsPipelineUtils/vars/notify.groovy:11`).

**Recommendation: A.** The slice's premise is that the trial changes syntax, not what the build
does. Both uses B could add would be invented for the demo. If the verdict turns on `when{}`, the
estate's real case is `Ansible/Jenkinsfile.iac-image`'s skip marker (`:25-38`). That file is a pod
pipeline, so a "migrate all" slice would convert it in any case. The plan is drafted on A: P4
says the conversion adds neither. Ruling A needs a line in the rulings section and a reworded
V01. Ruling B means rewriting P4.
