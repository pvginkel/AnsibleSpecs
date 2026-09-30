# P1 code review — round 2

Range: ArgoCDTools `91b21aa..131e2b9` (`phase/026-P1`). The only change is one test,
`test_an_exposures_entry_naming_a_missing_container_mints_one_every_backer_realizes`
(`aac-tools/tests/test_gen_architecture.py:287-307`). The plan doc's done-record now counts 7
tests (AnsibleSpecs `3cbbe74`), which matches `InHouseExposureTests`.

The phase may merge. Round 1's F1 is resolved. I re-ran round 1's mutations against `131e2b9` in a
scratch copy of `aac-tools`. M4 put the pod-wide pick back for a missing `exposures:` container
(`gen_architecture.py:1299`), and the new test errors because nothing is minted. M5 disabled the
missing-container gap (`:1342`), and the new test fails. I also ran M6, which stops every backer
realizing the minted service when an `exposures:` container is missing (`:1356`, `routed` left
empty). The test fails on its realizers assertion. Unmutated, all 32 tests pass. The test's
fixture drops `tunnel-reclaim`, which leaves the pod exactly one in-house service
(`svc:kubecoder-controller-api`). That is the case where the old outcome would have silently
referenced that service, so the test separates the new behaviour from the old one.

The test asserts the exact gap list. So it would also catch a regression that adds the port-match
gap alongside the missing-container gap, which `:1349` suppresses when an entry names a container.
The fix commit touches no generator code, so round 1's comparison and scratch-KubeCoderDeploy
proof still hold. Round 1's advisory F2 (the front-door fallback) is close-out S3 and is not
re-reported.

No findings.
