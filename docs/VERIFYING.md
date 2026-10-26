# Verify PixelBridge downloads

**[PixelBridge 1.2.0](https://github.com/QuasarLI/PixelBridge-Distribution/releases/tag/v1.2.0)
was signed and published on 2026-10-26.**
The successful [signing run 40334369634](https://github.com/QuasarLI/PixelBridge-Distribution/actions/runs/40334369634)
used `workflow_dispatch` at distribution/workflow source commit
[`54450c3fcec56423c0521c9506d312fad8fbbfca`](https://github.com/QuasarLI/PixelBridge-Distribution/commit/54450c3fcec56423c0521c9506d312fad8fbbfca);
the [exact release workflow](https://github.com/QuasarLI/PixelBridge-Distribution/blob/54450c3fcec56423c0521c9506d312fad8fbbfca/.github/workflows/release.yml)
is pinned to that commit, not a later documentation-only `main` commit.

The published [manifest](https://github.com/QuasarLI/PixelBridge-Distribution/releases/download/v1.2.0/release-manifest.json),
[provenance](https://github.com/QuasarLI/PixelBridge-Distribution/releases/download/v1.2.0/provenance.json)
and [SHA256SUMS](https://github.com/QuasarLI/PixelBridge-Distribution/releases/download/v1.2.0/SHA256SUMS)
have matching Sigstore bundles in the release. The private application source
commit is `6322a75cb58544401b8ae6a864ddf98cd558c45a`; the exact manifest SHA256 is
`7d480908eafca07ae04fa5ec6e802923200f1253884307ec28e21a086507c424`.

Post-publication local verification downloaded all **18 assets** and passed all
**11 blob signatures**: four ZIPs, their four contained EXEs and three metadata
files. Metadata, provenance, run/source/workflow identifiers, checksums and
server asset byte hashes agreed; all four original ZIP byte hashes were unchanged.
No raw EXE, private unlocked test build or private source was published. This
verification did not execute the application or alter a live installation.
Verify your own downloads before use; a passing infrastructure check alone is not
release or download verification.

Obtain a current trusted **cosign v3** installation using the official
[Sigstore installation guidance](https://docs.sigstore.dev/cosign/system_config/installation/).
Do not trust an executable or checksum merely because it sits beside an app
download. Follow cosign's official verification guidance for its own installation.

The v1.2.0 post-publication check used the official portable **cosign v3.1.4**
Windows amd64 verifier, pinned against both the
[immutable release asset metadata](https://api.github.com/repos/sigstore/cosign/releases/tags/v3.1.4)
and official
[`cosign_checksums.txt`](https://github.com/sigstore/cosign/releases/download/v3.1.4/cosign_checksums.txt).
Its SHA256 was
`cbe953787074611f1334cbf37dc1cf953995bb8c45398eb4fc7bb781d29c1f2a`.
The temporary verifier and extracted EXEs were removed after verification.

The only accepted certificate identity is the following **exact string**, not a
wildcard or a repository-wide regular expression:

```text
https://github.com/QuasarLI/PixelBridge-Distribution/.github/workflows/release.yml@refs/heads/main
```

The only accepted OIDC issuer is:

```text
https://token.actions.githubusercontent.com
```

The expected identity comes from this documented protected workflow, **not** from
whatever certificate or provenance is included in the untrusted download.
Sigstore bundles include verification material for the public transparency log.
Do not use flags that skip certificate identity, issuer, transparency-log or
signature verification. No standalone signing key is distributed.

## Windows example

Download the ZIP and its matching `.sigstore.json` bundle, plus
`release-manifest.json`, `provenance.json`, `SHA256SUMS` and their bundles from the
[official releases page](https://github.com/QuasarLI/PixelBridge-Distribution/releases).
Replace `1.2.0` below if verifying a different actual release version.
Stop on any nonzero cosign exit code; do not launch the application first.

```powershell
$identity = 'https://github.com/QuasarLI/PixelBridge-Distribution/.github/workflows/release.yml@refs/heads/main'
$issuer = 'https://token.actions.githubusercontent.com'
$zip = 'PixelBridge-v1.2.0-Free-win-x64.zip'
cosign verify-blob --bundle "$zip.sigstore.json" --certificate-identity $identity --certificate-oidc-issuer $issuer $zip
if ($LASTEXITCODE -ne 0) { throw 'ZIP signature verification failed' }

foreach ($name in @('release-manifest.json', 'provenance.json', 'SHA256SUMS')) {
    cosign verify-blob --bundle "$name.sigstore.json" --certificate-identity $identity --certificate-oidc-issuer $issuer $name
    if ($LASTEXITCODE -ne 0) { throw "Signature verification failed: $name" }
}

$manifest = Get-Content -LiteralPath '.\release-manifest.json' -Raw | ConvertFrom-Json
if ($manifest.product -cne 'PixelBridge' -or $manifest.version -cne '1.2.0') {
    throw 'Unexpected product/version'
}
$entry = @($manifest.artifacts | Where-Object { $_.file -ceq $zip })
if ($entry.Count -ne 1) { throw 'Missing or duplicate ZIP in manifest' }
$file = Get-Item -LiteralPath $zip
$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -cne $entry[0].sha256 -or $file.Length -ne $entry[0].size_bytes) {
    throw 'ZIP bytes do not match signed manifest'
}
$checksumLine = "$hash  $zip"
if (@(Get-Content -LiteralPath '.\SHA256SUMS' | Where-Object { $_ -ceq $checksumLine }).Count -ne 1) {
    throw 'ZIP checksum does not match signed SHA256SUMS'
}
```

Repeat for FreewithAds, Supporter and Pro as needed. Signing an archive is not the
same as Authenticode-signing the contained executable. For the additional EXE blob
signature, extract the already verified ZIP to a **new empty directory**, download
its EXE bundle, and verify before running the EXE:

```powershell
Expand-Archive -LiteralPath $zip -DestinationPath '.\verified-Free'
$exeBundle = 'PixelBridge-v1.2.0-Free-win-x64-PixelBridge.exe.sigstore.json'
cosign verify-blob --bundle $exeBundle --certificate-identity $identity --certificate-oidc-issuer $issuer '.\verified-Free\PixelBridge.exe'
if ($LASTEXITCODE -ne 0) { throw 'EXE signature verification failed' }
```

The bundle is named for the originating ZIP to avoid confusion between editions.
If verifying all editions, use separate clean extraction directories.

Check the signed provenance's `version`, `manifest_sha256`, `source_commit`,
`distribution_commit` and `workflow_run` against the official release notes and
successful GitHub run. A source commit in this private repository is a publisher
declaration, not a publicly reproducible build attestation. A SHA256 alone proves
only byte equality; it does not establish who produced or approved those bytes.

For the non-bundled contract starting with `1.3.0`, require manifest
`schema_version` to be `1` and `distribution_mode` to be exactly `nonbundled` in
both the signed manifest and signed provenance. Sunshine is not included; an
independent upstream download is not covered by PixelBridge's signatures. The
published `1.2.0` manifest and provenance predate this field and remain unchanged.
This contract description does not establish that a newer release is published.

## Distribution and Windows trust

For Gumroad or other redistribution, use only **identical final released ZIP bytes**
downloaded and verified after publication. Preserve the matching bundles and public
verification instructions. Repacking invalidates the signature.

These are Sigstore keyless blob signatures, **not Windows Authenticode signatures**.
Windows may still show **Unknown Publisher** or a **SmartScreen** warning. Do not
tell users that Sigstore removes these warnings or instruct them to disable their
security protections. A valid signature identifies the workflow and content;
it does not establish that software is harmless, licensed, or free of bugs.
The release review did not independently rebuild or fully audit the binaries,
establish real-customer activation, or establish actual emulator, controller,
gameplay, HDMI, audio or clean-PC pairing acceptance. Controller mappings remain
reference/schema-tested, not gameplay-tested. A verified release is not evidence
of a completed Gumroad upload/listing or Windows reputation.
