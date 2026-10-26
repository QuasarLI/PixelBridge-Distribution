# Verify PixelBridge downloads

**No signed release exists from this prepared pipeline yet.** Commands below
describe the production verification contract. A passing infrastructure check is
not evidence of an application signing run or a published release.

Obtain a current trusted **cosign v3** installation using the official
[Sigstore installation guidance](https://docs.sigstore.dev/cosign/system_config/installation/).
Do not trust an executable or checksum merely because it sits beside an app
download. Follow cosign's official verification guidance for its own installation.

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

## Distribution and Windows trust

For Gumroad or other redistribution, use only **identical final released ZIP bytes**
downloaded and verified after publication. Preserve the matching bundles and public
verification instructions. Repacking invalidates the signature.

These are Sigstore keyless blob signatures, **not Windows Authenticode signatures**.
Windows may still show **Unknown Publisher** or a **SmartScreen** warning. Do not
tell users that Sigstore removes these warnings or instruct them to disable their
security protections. A valid signature identifies the workflow and content;
it does not establish that software is harmless, licensed, or free of bugs.
