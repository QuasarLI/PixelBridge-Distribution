# PixelBridge

Public distribution repository for PixelBridge. The application source is private;
this repository contains only release infrastructure and public documentation.

**[PixelBridge 1.2.0](https://github.com/QuasarLI/PixelBridge-Distribution/releases/tag/v1.2.0)
was signed and published on 2026-10-26.**
The [production signing run](https://github.com/QuasarLI/PixelBridge-Distribution/actions/runs/40334369634)
succeeded, and all 18 published assets were downloaded and locally verified.

| Windows x64 edition | Production ZIP |
| --- | --- |
| Free | [Download Free](https://github.com/QuasarLI/PixelBridge-Distribution/releases/download/v1.2.0/PixelBridge-v1.2.0-Free-win-x64.zip) |
| FreewithAds | [Download FreewithAds](https://github.com/QuasarLI/PixelBridge-Distribution/releases/download/v1.2.0/PixelBridge-v1.2.0-FreewithAds-win-x64.zip) |
| Supporter | [Download Supporter](https://github.com/QuasarLI/PixelBridge-Distribution/releases/download/v1.2.0/PixelBridge-v1.2.0-Supporter-win-x64.zip) |
| Pro | [Download Pro](https://github.com/QuasarLI/PixelBridge-Distribution/releases/download/v1.2.0/PixelBridge-v1.2.0-Pro-win-x64.zip) |

Before running a download, follow [signature verification](docs/VERIFYING.md):
obtain its matching Sigstore bundles and the signed manifest, provenance and
`SHA256SUMS` from the release, verify signatures against the exact workflow
identity and issuer, and compare the downloaded bytes.

All usable Xbox controller mappings and profiles are included in **every edition**.
Paid production editions remain license-gated. The unlocked Pro LOCAL-TEST build
is private and is never a release asset.

See [the artifact handoff contract](docs/RELEASING.md) for the completed release
record and future release procedures. The repository policy gate remains enabled;
`RELEASE_SIGNING_ENABLED=false` was restored after publication and verification
to block future signing dispatches until separately authorized.

Sigstore keyless signatures establish the publishing workflow's identity and bind
it to the signed bytes. They are **not Windows Authenticode**: Windows may still
display **Unknown Publisher** or a SmartScreen warning. A signature is not a
security audit or a guarantee that an application is safe.
Independent full-binary rebuild/audit, real-customer activation and actual
emulator/controller/gameplay/HDMI/audio/clean-PC pairing acceptance have not been
established. Publication and local verification do not establish a completed
Gumroad upload or listing.
