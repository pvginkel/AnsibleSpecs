# P1 code review — round 1

Range `33bb16fd..c1badcb` on HomelabTerraformProvider `phase/022-P1`; gate green (`gate_r1.log`).

**Readiness: ready to merge.** The phase delivers what it promised. `homelab_s3_reader` creates a
user with `max-buckets=-1` and `user-caps=buckets=read`, and exposes the minted key pair with the
secret marked sensitive. `grant_backup_reader` writes exactly two Allow statements, signed with the
owner's key, and never touches a policy when no reader is configured
(`resource.go:175,222,272`). Dropping the ask revokes the policies. A policy removed out of band
comes back as drift, and restoring it is an in-place update, never a replacement. The reader lives
in provider configuration with a `HOMELAB_S3_BACKUP_READER` fallback, and it is kept out of
`validateGroup` so existing provider blocks stay valid (`provider.go:311-327`).

The protocol-level tests in `resource_test.go` start from pre-grant state JSON and cover the cases
the inertness criteria rest on (V08, V09, V20). A release with no ask plans nothing, with or without
a reader. An ask with no reader plans only the ask and sends no policy request. To confirm that test
has teeth, I removed the `HasReader` guard in Read, and `TestStorageGrantWithoutReaderIsInert`
failed.

The two findings below are test gaps on paths the code gets right today. Neither is blocking.

## F1 — Minor · advisory · anchor: none · confidence: high

**No test grants the reader on a bucket added to a release that already has the grant.** On that
path, Update calls `GrantReader(ctx, access, secret, planBuckets)` (`internal/s3storage/resource.go:275`),
which is correct. But every fixture has exactly one fixed bucket: `resource_test.go:33` and
`:191,202`, and the acceptance config at `resource_acc_test.go:485`. Mutation run: I changed
`planBuckets` to `stateBuckets` on that line, and `go test ./internal/s3storage/` still passed. The
acceptance pair would not catch it either.

What a regression would cost: V01 says a bucket a prd release adds later is mirrored with nothing
set per app. With this mutation, the apply that adds the bucket leaves it without a policy. The P2
mirror then fails on that bucket every night. It recovers only when a later prd deploy of the same
release refreshes, sees the drift (`resource.go:222-231`) and applies again.

## F2 — Minor · advisory · anchor: none · confidence: high

**The no-reader Create path is untested.** Every `h.apply` in `resource_test.go` starts from a
non-null prior state (`:339,364,377,385`), so Create never runs in the tests `kc project test`
executes. Mutation run: I removed `&& r.client.HasReader()` from Create's guard
(`resource.go:175`), and the package still passed. The only test that reaches Create with a grant is
`TestAccS3Storage_readerGrant`, and it configures a reader.

The code is correct today. V08/V20's "grants nothing" is shown only for existing releases, the
Update path. A new S3 release created on the dev cluster, where there is no reader, has no test
guarding it. A regression there would try to put a policy naming `arn:aws:iam:::user/`, and the
create would fail.
