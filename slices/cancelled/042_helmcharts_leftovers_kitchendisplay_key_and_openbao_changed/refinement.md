# Slice 042 — refinement

## D1 — Repair KitchenDisplay's deploy to the kitchen Pi, or retire the deploy stage and keep only the build

**Context.** KitchenDisplay's Jenkins job deploys the kiosk binary to the kitchen Pi with two ssh calls and one rsync, through two helpers in the shared pipeline library that read an SSH key out of a clone of the HelmCharts repo. When HelmCharts was decommissioned you ruled "keep them + follow-up": the helpers stayed, KitchenDisplay kept cloning the archived repo for its key, and moving the key became this slice. Grounding overturned the picture the card was written from: the key is no longer at HelmCharts' head — a commit deleted the key file, so the deploy stage has failed on every build since about early June, and the job is currently disabled. The clone the card wants dropped fetches nothing useful today. The key is still in HelmCharts' git history (the repo was always private, so the key was never public) and can be recovered from there. This is a repair of a deploy that has been dead four months, not a tidy-up of a working one, and the job has to be re-enabled for the fix to show.

**The ask.** The card asks to store the key as a Jenkins SSH credential, rework the ssh and rsync calls to use it, and drop the HelmCharts clone — with you creating the credential.

**Background.** KitchenDisplay is the only caller of the two helpers anywhere in the estate. The Pi is one host, not managed by Ansible. Jenkins credentials are typed in by you in the UI by standing decision, and no job in the estate uses an SSH credential yet. Not verified: whether the Pi is still in service and still authorises the old key — it did not answer on SSH from the dev pod today, and whether it is off, moved, or just unreachable from the pod's network is unknown.

**Why yours.** Whether a household device's deploy pipeline lives is your preference, and nobody missed this one for four months.

**Recommendation.** Repair. You recover the existing key from HelmCharts' history and store it as a Jenkins credential of the "SSH username with private key" kind; the deploy stage uses it, scoped to that stage alone; the ssh and rsync calls move into KitchenDisplay's own pipeline, the two shared helpers and their doc section are deleted from the library, and the HelmCharts clone goes; you re-enable the job and a build deploys to the Pi. Trade-off: it costs you steps — recover the key, create the credential, re-enable the job — and a reachable Pi to prove it, for a deploy nobody missed in four months.

**The other way.** Retire the deploy stage: the job keeps building the binary and you copy it to the Pi by hand when needed; helpers and clone go the same way and no credential is needed — the kiosk has no automated deploy.

**If this is wrong.** Little either way: a repaired stage can be deleted later, and a retired one can come back on a later card.

**Operator.** Don't attempt to fix KitchenDisplay. I wasn't aware this was planned for a slice. My apologies. I'll fix this when and if I ever get back to getting this device to work. Please remove it from the slice. Please move the card to Later.

## D2 — How the openbao role reports a change to the OIDC config when OpenBao never returns the client secret

**Context.** The openbao role writes three things on every run without looking first — the six AppRoles, the OIDC config and the OIDC admin role — and always reports ok, so a run that really changed one of them shows zero changed; the scheduled drift job runs the playbook in check mode, which skips these writes outright, so drift in them is invisible there too. The card asks for honest reporting through a read-and-compare, the way the role's policy writes already do. The AppRole and OIDC-role compares are settled — the role reads what is there and writes only on a difference. The OIDC config is the one with a hole in it.

**The ask.** The card's close-out note flags it: OpenBao omits the client secret from its read, so the comparison needs care.

**Background.** OpenBao redacts the client secret on read, so a read-and-compare cannot tell whether it changed. Comparing only the other fields and skipping the write when they match would silently never push a rotated secret — that is the outcome to avoid.

**Why yours.** It decides whether a rotation of the client secret alone shows up as a change on your own run.

**Recommendation.** Keep writing the OIDC config on every real run, and report changed only when a readable field — discovery URL, client id, default role — differs. Trade-off: a rotation of the client secret alone is written correctly but reports ok, not changed; acceptable because you rotate it deliberately and know you did.

**The other way.** Remember a hash of the last-written secret — on the OpenBao host or in the secret store — and compare it, so a secret-only rotation reports changed; costs a new piece of state to keep in step, for an event you drive by hand.

**If this is wrong.** A secret rotation reads as no change — cosmetic; the secret is still written.

**Operator.** Agreed.

## Open facts — questions only you can answer

**F1.** Is the kitchen display Pi still in service at its usual address? The pod could not reach it today; this settles whether the repair can be proven in the run or is owed to you afterwards.

**Operator.** No. It's in a box since the move. I will get back to this at some point. It's not a priority.

**F2.** Does the Pi still accept the old pipeline key, or has it been reinstalled since June? Settles reusing the key versus minting a new pair.

**Operator.** I don't know.

## Settled

- The key is reused, not re-minted: the card says store the key, you recover it from HelmCharts' history, and no session ever prints or handles the private key; a new key pair is the fallback only if the Pi no longer accepts the old one.
- The drift job starts showing AppRole and OIDC-role drift: in check mode the role reports a would-change for a differing AppRole or OIDC role, as it already does for a secret-id a real run would mint, so the scheduled drift check goes red on real drift there.
- Both halves stay in one slice, about four phases across three repos — Ansible (the openbao role), KitchenDisplay (its pipeline) and JenkinsPipelineUtils (the two helpers and their doc section) — plus your steps: create the credential, re-enable the job, run the openbao playbook for the live proof; if D1 goes retire, the KitchenDisplay phase shrinks to removing the deploy stage and no credential is needed.
