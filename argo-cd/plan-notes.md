- Please work argo-cd/app-lifecycle.md into the plan.
  Absorbed into plan.md; app-lifecycle.md deleted (it is in git history).
  The plan needs work though. Right now it suggests keeping TF stuff in HelmCharts.
  I don't want this. The GitOps repo, like the KubeCoderConfig repo, needs
  to contain the full description of the app, except for the few flags that
  we keep in HelmCharts (i.e. whether it's deployed, destroyed and the link to
  the repo). Everything that describes the app, goes to the config repo.
  Also, the document currently depends on polling for the ApplicationSet repo.
  I prefer that uses web hooks same as for the config repos.
- I want the namespace TF logic deleted from the plugin after we migrate the last
  app. This needs to be tracked as part of the plan.
