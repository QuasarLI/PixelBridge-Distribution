# PixelBridge

Public distribution repository for PixelBridge. The application source is private;
this repository contains only release infrastructure and public documentation.

**No production release has been signed or published by this pipeline yet.**
The signing workflow is deliberately disabled until its prerequisites have been
reviewed and configured. There are no placeholder downloads.

Production downloads will have four editions: **Free**, **FreewithAds**,
**Supporter**, and **Pro**. All usable Xbox controller mappings and profiles must
be available in every edition. Paid production editions remain license-gated.
An unlocked Pro development build is private and is never a release asset.

See [the artifact handoff contract](docs/RELEASING.md) for staging and publishing,
and [signature verification](docs/VERIFYING.md) for checking downloaded bytes.

Sigstore keyless signatures establish the publishing workflow's identity and bind
it to the signed bytes. They are **not Windows Authenticode**: Windows may still
display **Unknown Publisher** or a SmartScreen warning. A signature is not a
security audit or a guarantee that an application is safe.
