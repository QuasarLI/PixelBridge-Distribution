# Production release handoff

## Status and prerequisites

**[PixelBridge 1.2.0](https://github.com/QuasarLI/PixelBridge-Distribution/releases/tag/v1.2.0)
was signed and published on 2026-10-26**, and post-publication local verification
is complete. The successful
[workflow_dispatch run 40334369634](https://github.com/QuasarLI/PixelBridge-Distribution/actions/runs/40334369634)
executed the [release workflow](https://github.com/QuasarLI/PixelBridge-Distribution/blob/54450c3fcec56423c0521c9506d312fad8fbbfca/.github/workflows/release.yml)
at exact protected distribution commit
[`54450c3fcec56423c0521c9506d312fad8fbbfca`](https://github.com/QuasarLI/PixelBridge-Distribution/commit/54450c3fcec56423c0521c9506d312fad8fbbfca).
The release tag and provenance's `distribution_commit` record that workflow
commit, not subsequent documentation-only commits on `main`.

The non-bundled **1.3.0 candidate** below has been independently inspected and
proposed through the protected PR path. It is **not a published release**.
Candidate pins and successful validation do not authorize staging, signing or
publication; final coordinator review and separate exact-commit authorization
remain required.

The **repository policy gate remains enabled**. After the completed release and
local verification, the `production-release` environment was restored to
`RELEASE_SIGNING_ENABLED=false` and checked. This blocks **future signing
dispatches**; it does not undo the published release. Future staging, enablement,
dispatch, signing and publication require separate exact-commit coordinator
authorization under the prerequisites below. The review and acceptance limits
remain in force.

1. Review current official [Sigstore blob signing documentation](https://docs.sigstore.dev/cosign/signing/signing_with_blobs/),
   [verification documentation](https://docs.sigstore.dev/cosign/verifying/verify/),
   [cosign releases](https://github.com/sigstore/cosign/releases), and
   [GitHub Actions OIDC guidance](https://docs.github.com/en/actions/concepts/security/openid-connect).
   The pins reviewed on 2026-10-26 are cosign **v3.1.4** and
   `actions/checkout` **v7.0.1**, with full checkout commit
   `3d3c42e5aac5ba805825da76410c181273ba90b1`. Cosign's Linux amd64 SHA256,
   `424e2c97d0b45fd7a6b608a87f090f35633f4c23ece5f092d48bba11aaf4bbfa`,
   matches both the official immutable GitHub release asset metadata and
   `cosign_checksums.txt`. CI downloads and checks that exact pin before executing
   its version/help commands; it does not sign or publish test assets.
   No mutable latest download or installer script is used at runtime.
   Review these pins against the official
   [actions/checkout repository](https://github.com/actions/checkout) and cosign
   release before updating them.
2. `main` is configured to require the pull-request path and an up-to-date passing
   `release-guard` check specifically from the GitHub Actions app. Enforcement
   includes administrators; force pushes and deletion are blocked, linear history
   and conversation resolution are required. Workflow, policy, script and
   documentation changes still require trusted human review. The workflow checks
   `github.ref_protected`, but that flag alone does not prove all these settings.
3. The `production-release` environment is configured with a `main`-branch-only
   deployment policy and `RELEASE_SIGNING_ENABLED=false`. There is currently one
   maintainer, `TheRealRickPrime`: the PR path has zero required approving reviews
   and the environment has no required reviewer. This is an explicitly authorized
   **sole-maintainer setup**, not an independent-approval guarantee. No self-review
   bypass or paid plan is used. The coordinator must review the exact workflow
   commit, private source commit and manifest hash before manual dispatch. If
   another trusted maintainer becomes available, add mandatory independent PR and
   environment reviewers and prevent self-review; never weaken existing controls
   to make a release run.
4. Before release operations, the coordinator must approve the exact version,
   private application source commit, complete public payload, independently
   reviewed per-edition filename allowlist, and manifest SHA256 documented below.
   The policy's `candidate` pins the version, source commit and manifest digest;
   all dispatch inputs must match those pins.
   Changing a candidate requires another reviewed policy change. A matching
   checksum or a builder-supplied filename is **not** evidence that a file is
   appropriate to publish.
5. The policy `enabled` gate is authorized independently through the protected PR
   path and required CI. Run `python -m unittest discover -s tests -v`, validate the
   actual handoff, review this workflow end-to-end, and obtain successful required
   CI for the final protected distribution commit. Keep environment variable
   `RELEASE_SIGNING_ENABLED=false` until separate exact-commit coordinator
   authorization explicitly permits enablement and the release steps. Enabling
   the repository policy alone does not authorize staging or dispatch.

The workflow uses only GitHub-hosted runners, GitHub release storage, GitHub OIDC,
and Sigstore's public signing/transparency services. No private-repository checkout,
PAT, billing service, customer key or seller secret belongs in the public workflow.
The job needs `contents: write` to download/upload draft assets and publish, and
`id-token: write` to request a short-lived signing identity. No other token
permissions are requested. Checkout does not persist credentials.

## Exact producer contract

Version `1.2.0` and tag `v1.2.0` identify the **published release**. Reusing these
names is not authorization to stage, replace or republish its assets.
Version strings must be stable `MAJOR.MINOR.PATCH` without a leading `v`.
The four archive names, with case preserved, are:

```text
PixelBridge-v1.2.0-Free-win-x64.zip
PixelBridge-v1.2.0-FreewithAds-win-x64.zip
PixelBridge-v1.2.0-Supporter-win-x64.zip
PixelBridge-v1.2.0-Pro-win-x64.zip
```

Each ZIP has `PixelBridge.exe` at its root, not an enclosing directory, plus only
explicitly reviewed runtime assets, public documentation, controller mappings and
fresh templates. All usable Xbox mappings/profiles are included in every edition.
Paid production builds remain license-gated.

The reviewed payload path policy in [release-policy.json](../release-policy.json),
unchanged between published v1.2.0 and candidate v1.3.0, has
14 files common to all editions: the native EXE, Backend and Performance runtime
PowerShell scripts, original logo/icon, controller documentation, five RetroArch
mappings and the common XInput configuration, README and third-party notices.
FreewithAds alone adds `Assets/AdGuard-728x90.png` for 15 files. There is no separate
firewall script. These paths are not publication approval; compare every final archive entry and
hash against the reviewed private build and manifest before enabling publication.

### Published v1.2.0 payload review

The published release is version `1.2.0`, private application source commit
`6322a75cb58544401b8ae6a864ddf98cd558c45a`, and exact manifest SHA256
`7d480908eafca07ae04fa5ec6e802923200f1253884307ec28e21a086507c424`.
Those identifiers pin the released payload; they do not authorize a future
staging, dispatch or signing run.

Independent read-only inspection of the local customer export confirmed exactly
four production ZIPs and the manifest; each ZIP's complete entry list, sizes,
hashes and strict container structure passed the distribution validator. All
13 common non-EXE files have identical hashes in all four editions. All six
controller profile/config files are present in every edition.

Both runtime scripts and all shipped text documentation/mappings were read.
The Backend script parses bounded local settings with DTDs disabled, checks
Sunshine over loopback, starts only user-selected local executables, opens Xbox
in the dedicated Edge profile, and offers the explicit scoped firewall action.
That firewall path checks the previewed settings hash, administrative elevation,
an existing private IPv4 address/subnet, exact Sunshine executable and Private
profile; it creates only two named TCP/UDP rules and will not overwrite existing
rules. No router, VPN or global security-policy change appears in those scripts.
The Performance script targets the dedicated Xbox Edge process family and changes
only Normal to AboveNormal priority, with PID/start-time-aware undo records.

Read-only managed metadata inspection found x64 CLI executables declaring version
`1.2.0`, the correct edition constant, `IsLocalTest=false`, and only the embedded
PixelBridge icon resource. Compiled entitlement getters were inspected: paid
builds fall back to Free without a cache or with revoked state. This is not a
full binary decompilation or a proof that a trusted purchase created the cache.
The EXEs have no Authenticode signature. PNG inspection found only ordinary image
chunks, no text/EXIF metadata or trailing bytes. FreewithAds alone contains the
disclosed AdGuard banner.

No live settings, browser data, license cache, Sunshine state, source tree, local
test artifact or new Gumroad marketing icon is in the allowlisted export. Reviewed
text contains public project/provider and checkout links, public product IDs and
the disclosed affiliate identifier, not a seller credential. No customer secrets
were supplied or used for this review.

Review limits remain important: this did not execute the app or scripts, alter an
installation, independently rebuild the private source, prove complete binary
safety, exercise a real customer's Gumroad activation, or test Xbox/TV/controller
hardware. The package documentation explicitly calls controller mappings
reference/schema-tested rather than gameplay-tested. No independent full-binary
rebuild/audit, real-customer key activation or actual emulator/controller/gameplay/
HDMI/audio/clean-PC pairing acceptance was established. There is no reproducible
build attestation. The completed signing run and post-publication verification
establish signed-byte identity, not those acceptance results. Future release
authorization must acknowledge these limits; do not mutate or repack the published
ZIP bytes.

### Non-bundled v1.3.0 candidate review

The proposed candidate is version `1.3.0`, private application source commit
`5f74e07189f62540b6b4e8df0236d0c5ba37370d`, and exact manifest SHA256
`a82a2af9313565e6d00e8f96fc1986b7f3dbbf217d9035c79c5d4a1dde778ef0`.
The manifest is 8,197 bytes, schema version `1`, with
`distribution_mode` exactly `nonbundled`. The policy's candidate tuple identifies
these inspected bytes, not any superseded 1.3.0 export.

| Production ZIP | Bytes | SHA256 |
| --- | ---: | --- |
| `PixelBridge-v1.3.0-Free-win-x64.zip` | 172023 | `ff118409724c4dbc65bd72cb30cea81bb894866cc9bcfe3727b691b3f0f9deda` |
| `PixelBridge-v1.3.0-FreewithAds-win-x64.zip` | 196834 | `6c661177502214e3c76ef9514432d0417da5ed18986282a0f7ecf8d0917e1ea3` |
| `PixelBridge-v1.3.0-Pro-win-x64.zip` | 172023 | `faa421eb38fa26f978764be4c2aa36c2eb728144785499f0b3a473c6a205170c` |
| `PixelBridge-v1.3.0-Supporter-win-x64.zip` | 172025 | `10063acf1de98c290d4baf157eac797f24b635d6261050eef12afaa70e066a24` |

Independent read-only review accepted exactly these four ZIPs and manifest,
including strict ZIP container structure and every declared payload size and
SHA256. All paths still equal the original reviewed 14-file allowlist, or 15 for
FreewithAds. The 13 common non-EXE payloads are identical across editions. Compared
with published 1.2.0, only the EXE, Backend script and three customer text guides
change; all assets, six controller profile/config files and Performance script
retain their previously reviewed bytes.

Private production receipts agree with every shipped file record, edition,
`local_test=false` and `nonbundled` mode. Their source fingerprint was independently
recomputed from the 42 committed build inputs using the repository's Windows
checkout line endings. Every non-EXE payload also matches its committed source
file. These checks are consistency evidence, not an independent full-binary
rebuild or a reproducible-build attestation. Receipts and review evidence are
private and are not release assets.

Reflection-only inspection of each contained managed EXE found x64 CLI version
`1.3.0.0`, the correct edition constant, `IsLocalTest=false`,
`DistributionMode=nonbundled`, and only the embedded PixelBridge icon resource.
The EXEs have no Authenticode certificate table. Licensing code is unchanged.
Customer guides explicitly exclude Sunshine and direct users to its official
upstream release page for independent verification and setup. PixelBridge does
not download or invoke its installer; configured-host launch/reuse remains
available. Browser preference, guided TV hardware routes and purchase continuity
are retained. The saved all-edition XInput menu-navigation switch leaves mouse
and keyboard available; the controller guide documents foreground/modal/busy
guards and keyboard-only field boundaries, without claiming physical acceptance.

No upstream installer, Lite archive, source tree, inventory, compliance sidecar,
private receipt, personal wrapper, LOCAL-TEST build, live settings, browser
profile, license cache or Sunshine state is in this exact customer payload.
Actual cloud sign-in/playback, physical controller/TV/extender/audio/gameplay,
clean-PC independent Sunshine setup/pairing and real-customer activation remain
untested. No app or runtime script was executed during this independent payload
inspection. The application license is unchanged; future Sunshine bundling and
its source/notices/rights/access review remain blocked and separate.

This candidate is **not signed, staged or published**. Keep
`RELEASE_SIGNING_ENABLED=false`, leave the integration PR unmerged for coordinator
review, and do not reuse the completed 1.2.0 release authorization. No 1.3.0
download URL or production signing run is established by these pins.

The ZIP producer must omit directory entries, comments, ZIP extra fields, data
descriptors, prefixes/trailing data, encrypted entries and symlinks. Use a seekable
ZIP output, stored or Deflate compression and portable ASCII paths
with forward slashes inside ZIP metadata. Paths are case-unique, without traversal,
hidden segments, Windows device names, drive prefixes or trailing dots.
Maximum compressed size is 256 MiB per ZIP; maximum expanded size is 512 MiB.
If a legitimate production build exceeds these limits, review the limits before
staging rather than bypassing validation.

`release-manifest.json` is UTF-8 without BOM, with no duplicate or extra fields.
The producer should use compact JSON and the property order shown below. Validation
binds its **exact bytes** to the separately approved SHA256; it does not reserialize
before checking. The following illustrates structure only and must never be
uploaded as a release asset:

```json
{
  "schema_version": 1,
  "product": "PixelBridge",
  "version": "1.2.0",
  "source_repository": "QuasarLI/PixelBridge",
  "source_commit": "<40 lowercase hex>",
  "artifacts": [
    {
      "file": "PixelBridge-v1.2.0-Free-win-x64.zip",
      "edition": "Free",
      "target": "win-x64",
      "size_bytes": 123,
      "sha256": "<64 lowercase hex>",
      "files": [
        {
          "path": "PixelBridge.exe",
          "size_bytes": 123,
          "sha256": "<64 lowercase hex>"
        }
      ]
    }
  ]
}
```

The real manifest contains **exactly four** artifacts, sorted ordinally by `file`
(Free, FreewithAds, Pro, Supporter). Each `files` array enumerates **every** regular
payload file, sorted ordinally by `path`, with its uncompressed size and SHA256.
There are no timestamps, local paths, arbitrary URLs, extra metadata or extra
editions. SHA256s and commits use lowercase hexadecimal.

### Non-bundled v1.3.0 and later

Starting with version `1.3.0`, schema version `1` requires one additional top-level
field, `"distribution_mode":"nonbundled"`, immediately after `version` in the
producer's canonical property order. The exact top-level keys are
`schema_version`, `product`, `version`, `distribution_mode`, `source_repository`,
`source_commit` and `artifacts`. The value is the literal lowercase `nonbundled`;
omitting it, using a different value or adding unknown fields is rejected.
Legacy manifests before `1.3.0`, including the published `1.2.0` manifest, retain
the original six-field shape and bytes. Artifact and payload file records do not
change.

The agreed non-bundled `1.3.0` payload path set remains the same 14 files per
edition, or 15 for FreewithAds. Updated README and third-party notices may provide
official upstream download guidance, but Sunshine itself is **not included**.
No installer, Lite build, source archive, inventory, compliance sidecar or
`third_party_sources` field is accepted by this contract. Private build receipts
mirror the mode but are never public release assets. Future bundled distribution
requires separate review and support; this change does not authorize it.

The signed manifest binds the mode to the exact reviewed bytes. Generated signed
provenance copies `distribution_mode`, and release notes disclose that Sunshine
must be obtained separately. The four-ZIP, 18-asset and 11-signature contracts and
all payload allowlists and publication guards remain unchanged. This is
contract support and candidate pinning, **not release authorization or publication
of a v1.3.0 candidate**. Actual source and manifest hashes must be independently
reviewed and pinned through the protected PR path before separately authorized
release steps. The candidate review above remains subject to final coordinator
review. Never reuse v1.2.0 authorization or placeholder candidate pins.

The reviewed policy contains the independent exact path list for each edition.
Manifest paths must equal that policy, not merely pass a substring filter.
The validator also rejects obvious local-test/unlocked/private/credential/pairing
markers and sensitive/source-file extensions as defense in depth. These checks
cannot determine whether innocently named bytes contain secrets or live user data:
the private build owner and coordinator must inspect the payload before approval.
Runtime PowerShell scripts intentionally shipped with the application must be
explicitly reviewed; this does not authorize publishing the private source tree.

Never stage any LOCAL-TEST archive, including the separate
`PixelBridge-v1.2.0-Pro-LOCAL-TEST-win-x64.zip` or its v1.3.0 equivalent.
Never stage private source, customer/account keys, browser profiles, seller tokens,
credentials, signing keys, logs, Sunshine pairing/configuration/state, or any
user-specific data. Do not touch the existing local CloudPlay installation.

## Staging and signing

The steps below remain the procedure for a **future separately authorized
release**, not instructions to rerun published v1.2.0. Keep
`RELEASE_SIGNING_ENABLED=false` until new exact-commit coordinator authorization
permits enablement and the release steps. Corrections require a new version;
never restage or replace the published v1.2.0 assets.

A draft release in a **public repository is not a private storage/security
boundary**. Stage only vetted production artifacts whose publication is approved.
Keep staging and validation directories on local storage separate from the private
test build; do not use wildcard upload commands.

1. Build in the private application project. Review all payloads and compute the
   manifest from the completed ZIP bytes. Obtain source commit, manifest SHA256,
   artifact sizes/SHA256s and final release authorization from the coordinator.
2. With the reviewed public policy, run the offline validator, for example:

   ```powershell
   python .\scripts\release.py validate --policy .\release-policy.json --directory D:\PixelBridge\production-staging --version 1.3.0 --source-commit APPROVED_40_HEX --manifest-sha256 APPROVED_64_HEX
   ```

   That directory must contain exactly the four production ZIPs and manifest.
   Replace the approval markers; do not use guessed values. Offline `validate`
   accepts a disabled policy so artifacts can be audited **without** enabling
   publishing; exact reviewed payload lists and pins are still mandatory.
3. Use the existing locally authenticated `gh` session to create a non-prerelease
   **draft**, targeting the **exact protected distribution commit** that will
   execute the signing workflow, not the private application's commit. Explicitly
   upload only the five allowlisted files. Do not use `--clobber`.
   Do not push a release tag separately; do not move an existing release tag.
4. Dispatch `release.yml` from protected `main`, supplying the approved version,
   source commit and manifest SHA256 and explicitly checking `confirm_publish`.
   A dispatch from a feature branch, an unprotected ref, a disabled policy, absent
   cosign pin, missing payload policy, or missing OIDC permission cannot publish.
   The coordinator must compare the exact inputs to the approved handoff before
   dispatch. If required environment reviewers are configured later, they must
   also compare these inputs, not rubber-stamp the dispatch.
5. The runner downloads the five assets, rejects extras, checks exact manifest
   bytes and all archive/payload hashes, and signs the ZIPs and extracted EXEs.
   It also signs `release-manifest.json`, `provenance.json` and `SHA256SUMS`.
   Each bundle is verified immediately against the exact identity and issuer.
   EXEs are never executed, and signed bytes are never modified.
6. The runner detects draft/asset changes, uploads only its explicit output set
   without replacement, downloads every final asset again, verifies hashes and
   signatures, and only then publishes. A failure leaves the draft unpublished.
   A partial upload requires a maintainer to inspect the failure and explicitly
   remove the generated outputs before retrying; never delete the whole release
   or blindly replace assets to make a check pass.

Unpublished drafts do not have a git tag, and GitHub's REST release-by-tag endpoint
can return 404 for them. The validator instead discovers releases through the
authenticated, fully paginated release list, requires exactly one exact pending
tag-name match, and fetches it by immutable release ID. It rejects missing or
ambiguous matches, published releases and prereleases, and pins that same ID
through every repeated signing/upload/final-verification check. This does not
create or move a tag. The explicit `gh release download/upload/edit <tag>` paths
also support pending draft tags through the CLI's shared draft lookup and
release-ID API calls; successful staging/upload and downloaded-byte validation
against the actual five-asset draft establish that contract before dispatch.

The release tag must be unused. The workflow refuses an existing tag before
signing and again before publication, targets the exact distribution workflow
commit, checks that protected main has not moved, and checks the new tag's commit
after publication. No tag is moved or reused.

Limit concurrent release writers. The workflow serializes its own runs and compares
release IDs and asset IDs/sizes/update timestamps/digests; it cannot revoke an authorized
maintainer's concurrent API access or make multiple GitHub REST calls atomic.
Configure GitHub immutable releases where supported, review their current behavior,
and never replace published bytes. A correction is a new version.

## Final public outputs and local delivery

Published v1.2.0 has exactly **18 release assets**: four ZIPs; manifest, provenance and
checksums; a Sigstore JSON bundle for each of those seven files; and four bundles
for the `PixelBridge.exe` already inside the ZIPs. No separate unlocked or ordinary
EXE is uploaded. EXE bundle naming is:

```text
PixelBridge-v1.2.0-Free-win-x64-PixelBridge.exe.sigstore.json
```

The public provenance records the private source commit as a declared build input,
the distribution workflow commit, run URL/attempt, exact signing identity/issuer,
manifest hash and cosign pin. This is **release-signing provenance**, not a claim
that the public signing workflow built the private source or that the binaries
were reproducibly built from it.

For v1.2.0, all 18 published assets were downloaded into a clean local distribution
directory. All 11 blob signatures (four ZIPs, four contained EXEs and three
metadata files) passed using the official immutable cosign v3.1.4 portable
verifier, pinned against release asset metadata and checksums as recorded in
[VERIFYING.md](VERIFYING.md). Manifest/provenance/run/source/workflow/checksum
agreement and server asset byte hashes passed; all four original ZIP byte hashes
were unchanged. Temporary verifier and extracted EXEs were removed. No application
was executed and no live installation was changed.

For each future release, repeat post-publication download and verification of all
assets as described in [VERIFYING.md](VERIFYING.md). Only those exact verified ZIP
bytes may be copied to Gumroad. Do not recompress, change license files, or
otherwise modify a signed ZIP. Publication and verification do **not** establish
that a checkout upload or Gumroad listing is complete.

Report the actual public release URL, signing workflow run URL, source/distribution
commits, certificate identity and artifact hashes only after publication and local
verification succeed. Keep absolute local paths and user-specific data in private
handoffs, never public documentation. Keep the separately authorized private
Pro test path clearly separate; it is not signed or verified by this public
pipeline. Never invent download links or claim a staged draft is a shipped release.
