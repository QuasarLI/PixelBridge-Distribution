"""Validate a reviewed production handoff, then keylessly sign a draft release."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


REPOSITORY = "QuasarLI/PixelBridge-Distribution"
SOURCE_REPOSITORY = "QuasarLI/PixelBridge"
EDITIONS = ("Free", "FreewithAds", "Supporter", "Pro")
IDENTITY = (
    "https://github.com/QuasarLI/PixelBridge-Distribution/"
    ".github/workflows/release.yml@refs/heads/main"
)
ISSUER = "https://token.actions.githubusercontent.com"
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
UNSAFE_NAME = re.compile(
    r"local[-_]?test|unlocked|private|credential|secret|seller[-_]?token|"
    r"customer[-_]?key|pairing|sunshine|browser[-_]?profile",
    re.IGNORECASE,
)
UNSAFE_SUFFIXES = {
    ".pfx", ".p12", ".pem", ".key", ".pdb", ".sln", ".cs", ".vb",
    ".csproj", ".vbproj", ".user", ".suo", ".log", ".dmp", ".sqlite",
    ".db", ".env",
}


class ReleaseError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def exact_keys(value, keys, label):
    require(type(value) is dict and set(value) == set(keys),
            f"{label}: unexpected or missing fields")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_hash(value, length=64):
    return type(value) is str and re.fullmatch(rf"[0-9a-f]{{{length}}}", value)


def valid_version(value):
    return type(value) is str and re.fullmatch(
        r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value
    )


def safe_path(value):
    require(type(value) is str and
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", value),
            f"Invalid payload path: {value!r}")
    parts = value.split("/")
    require(all(part and part not in (".", "..") and
                not part.startswith(".") and not part.endswith((".", " "))
                for part in parts), f"Unsafe payload path: {value}")
    require(not any(part.split(".")[0].upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{number}" for number in range(1, 10)),
        *(f"LPT{number}" for number in range(1, 10)),
    } for part in parts), f"Reserved Windows payload path: {value}")
    require(not UNSAFE_NAME.search(value) and
            Path(value).suffix.lower() not in UNSAFE_SUFFIXES,
            f"Forbidden production payload path: {value}")
    return value


def archive_names(version):
    require(valid_version(version), "Version must be MAJOR.MINOR.PATCH without v")
    return {
        edition: f"PixelBridge-v{version}-{edition}-win-x64.zip"
        for edition in EDITIONS
    }


def validate_policy(policy):
    exact_keys(policy, ("schema_version", "enabled", "cosign_version",
                        "cosign_linux_amd64_sha256", "payload_files"), "Policy")
    require(type(policy["schema_version"]) is int and policy["schema_version"] == 1,
            "Unsupported policy schema")
    require(policy["enabled"] is True, "Release policy is disabled")
    validate_tool_pin(policy)
    exact_keys(policy["payload_files"], EDITIONS, "Edition payload policy")
    for edition, paths in policy["payload_files"].items():
        require(type(paths) is list and paths and len(paths) <= 1000,
                f"{edition}: reviewed exact payload paths are required")
        for path in paths:
            safe_path(path)
        require(paths == sorted(paths) and len({p.lower() for p in paths}) == len(paths),
                f"{edition}: payload paths must be sorted and case-unique")
        require("PixelBridge.exe" in paths, f"{edition}: PixelBridge.exe is required")
        lowered = {path.lower() for path in paths}
        require(not any("/".join(path.lower().split("/")[:index]) in lowered
                        for path in paths for index in range(1, len(path.split("/")))),
                f"{edition}: file/directory path collisions are not allowed")
    return policy


def validate_tool_pin(policy):
    require(type(policy["cosign_version"]) is str and re.fullmatch(
        r"v3\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", policy["cosign_version"]),
        "A reviewed exact stable cosign v3 version is required")
    require(valid_hash(policy["cosign_linux_amd64_sha256"]),
            "A reviewed cosign executable SHA256 is required")


def validate_zip_container(path, members):
    with path.open("rb") as stream:
        stream.seek(-22, os.SEEK_END)
        end = struct.unpack("<4s4H2IH", stream.read(22))
        require(end[0] == b"PK\x05\x06" and end[1:3] == (0, 0) and
                end[3] == end[4] == len(members) and end[7] == 0 and
                end[5] + end[6] + 22 == path.stat().st_size,
                f"{path.name}: nonstandard ZIP trailer or hidden data")
        offset = 0
        for member in sorted(members, key=lambda entry: entry.header_offset):
            require(member.header_offset == offset and not member.flag_bits & 8,
                    f"{path.name}: ZIP prefix, gap or data descriptor is not allowed")
            stream.seek(offset)
            header = struct.unpack("<4s5H3I2H", stream.read(30))
            name = member.filename.encode("ascii")
            require(header[0] == b"PK\x03\x04" and header[2] == member.flag_bits and
                    header[3] == member.compress_type and header[6] == member.CRC and
                    header[7] == member.compress_size and header[8] == member.file_size and
                    header[9] == len(name) and header[10] == 0 and
                    stream.read(len(name)) == name,
                    f"{path.name}: local ZIP header differs from its directory")
            offset += 30 + len(name) + member.compress_size
        require(offset == end[6] and
                end[5] == sum(46 + len(member.filename) for member in members),
                f"{path.name}: unexpected ZIP container data")


def validate_archive(path, files, allowed_paths, exe_destination=None):
    require(type(files) is list and files, f"{path.name}: files list is required")
    for entry in files:
        exact_keys(entry, ("path", "size_bytes", "sha256"), "Payload file")
        safe_path(entry["path"])
        require(type(entry["size_bytes"]) is int and entry["size_bytes"] >= 0,
                "Payload size must be a nonnegative integer")
        require(valid_hash(entry["sha256"]), "Invalid payload SHA256")
    paths = [entry["path"] for entry in files]
    require(paths == allowed_paths, f"{path.name}: payload differs from reviewed allowlist")
    require(sum(entry["size_bytes"] for entry in files) <= MAX_EXPANDED_BYTES,
            f"{path.name}: expanded payload exceeds limit")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        require(len(members) == len(files), f"{path.name}: unexpected ZIP entries")
        require(not archive.comment, f"{path.name}: ZIP comments are not allowed")
        actual = {}
        for member in members:
            safe_path(member.filename)
            require(member.filename not in actual, f"{path.name}: duplicate ZIP entry")
            require(not member.is_dir(), f"{path.name}: directory entries are not allowed")
            mode = member.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG),
                    f"{path.name}: links and special files are not allowed")
            require(not member.flag_bits & 1, f"{path.name}: encrypted entry")
            require(not member.comment and not member.extra,
                    f"{path.name}: ZIP comments and extra fields are not allowed")
            require(member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                    f"{path.name}: unsupported ZIP compression")
            actual[member.filename] = member
        require(set(actual) == set(paths), f"{path.name}: ZIP payload mismatch")
        validate_zip_container(path, members)
        for entry in files:
            member = actual[entry["path"]]
            require(member.file_size == entry["size_bytes"],
                    f"{path.name}: payload size mismatch: {member.filename}")
            digest = hashlib.sha256()
            length = 0
            with archive.open(member) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    length += len(chunk)
                    require(length <= entry["size_bytes"], "Expanded file exceeds manifest")
                    digest.update(chunk)
            require(length == entry["size_bytes"] and digest.hexdigest() == entry["sha256"],
                    f"{path.name}: payload hash mismatch: {member.filename}")
        if exe_destination is not None:
            with archive.open("PixelBridge.exe") as stream:
                Path(exe_destination).write_bytes(stream.read())


def validate_handoff(directory, policy, version, source_commit, manifest_hash,
                     exe_directory=None, exact_assets=True):
    names = archive_names(version)
    require(valid_hash(source_commit, 40), "An exact lowercase source commit is required")
    require(valid_hash(manifest_hash), "An independently approved manifest SHA256 is required")
    validate_policy(policy)
    directory = Path(directory)
    expected = {*names.values(), "release-manifest.json"}
    if exact_assets:
        require({p.name for p in directory.iterdir()} == expected and
                all(p.is_file() and not p.is_symlink() for p in directory.iterdir()),
                "Staging directory must contain exactly four ZIPs and release-manifest.json")
    manifest_path = directory / "release-manifest.json"
    require(manifest_path.stat().st_size <= 1024 * 1024, "Manifest exceeds size limit")
    require(sha256(manifest_path) == manifest_hash, "Manifest differs from approved SHA256")
    manifest = read_json(manifest_path)
    exact_keys(manifest, ("schema_version", "product", "version", "source_repository",
                          "source_commit", "artifacts"), "Manifest")
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
            "Unsupported manifest schema")
    require(manifest["product"] == "PixelBridge" and manifest["version"] == version and
            manifest["source_repository"] == SOURCE_REPOSITORY and
            manifest["source_commit"] == source_commit, "Manifest source/version mismatch")
    artifacts = manifest["artifacts"]
    require(type(artifacts) is list and len(artifacts) == 4,
            "Exactly four production artifacts are required")
    for artifact in artifacts:
        exact_keys(artifact, ("file", "edition", "target", "size_bytes", "sha256", "files"),
                   "Artifact")
        require(type(artifact["edition"]) is str and artifact["edition"] in names and
                artifact["file"] == names[artifact["edition"]] and
                artifact["target"] == "win-x64", "Unexpected edition/asset/target")
        require(type(artifact["size_bytes"]) is int and
                0 < artifact["size_bytes"] <= MAX_ARCHIVE_BYTES, "Invalid ZIP size")
        require(valid_hash(artifact["sha256"]), "Invalid ZIP SHA256")
        path = directory / artifact["file"]
        require(path.is_file() and not path.is_symlink(), "Missing ZIP or symlink")
        require(path.stat().st_size == artifact["size_bytes"] and
                sha256(path) == artifact["sha256"], f"ZIP differs from manifest: {path.name}")
        exe_path = None
        if exe_directory is not None:
            exe_path = Path(exe_directory) / (path.stem + "-PixelBridge.exe")
        validate_archive(path, artifact["files"], policy["payload_files"][artifact["edition"]],
                         exe_path)
    require([a["file"] for a in artifacts] == sorted(names.values()),
            "Artifacts must be sorted with each production edition exactly once")
    return manifest


def run(*args):
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE).stdout


def gh_json(endpoint):
    return json.loads(run("gh", "api", endpoint))


def get_release(tag):
    release = gh_json(f"repos/{REPOSITORY}/releases/tags/{tag}")
    require(release["draft"] is True and release["prerelease"] is False,
            "Only a non-prerelease DRAFT may be processed")
    return release


def asset_snapshot(release):
    assets = release["assets"]
    require(len({a["name"] for a in assets}) == len(assets), "Duplicate release asset name")
    return {a["name"]: (a["id"], a["size"], a["updated_at"], a.get("digest"))
            for a in assets}


def require_unused_tag(tag):
    refs = gh_json(f"repos/{REPOSITORY}/git/matching-refs/tags/{tag}")
    require(type(refs) is list and
            all(ref["ref"] != f"refs/tags/{tag}" for ref in refs),
            "Release tag already exists; never move or reuse a release tag")


def require_release_source(commit):
    branch = gh_json(f"repos/{REPOSITORY}/branches/main")
    require(branch["protected"] is True and branch["commit"]["sha"] == commit,
            "Protected main moved or is no longer protected; restart from reviewed main")


def download_assets(tag, directory, names):
    for name in sorted(names):
        run("gh", "release", "download", tag, "--repo", REPOSITORY,
            "--pattern", name, "--dir", str(directory))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, separators=(",", ":"), ensure_ascii=True) + "\n",
                          encoding="utf-8")


def verify_blob(cosign, blob, bundle):
    run(str(cosign), "verify-blob", "--bundle", str(bundle),
        "--certificate-identity", IDENTITY, "--certificate-oidc-issuer", ISSUER,
        str(blob))


def install_cosign(policy, directory):
    validate_tool_pin(policy)
    version = policy["cosign_version"]
    path = directory / "cosign"
    url = f"https://github.com/sigstore/cosign/releases/download/{version}/cosign-linux-amd64"
    with urllib.request.urlopen(url, timeout=60) as response, path.open("wb") as output:
        length = 0
        while chunk := response.read(1024 * 1024):
            length += len(chunk)
            require(length <= MAX_ARCHIVE_BYTES, "Cosign download exceeds size limit")
            output.write(chunk)
    require(sha256(path) == policy["cosign_linux_amd64_sha256"],
            "Cosign executable does not match the reviewed pin")
    path.chmod(0o700)
    run(str(path), "version")
    return path


def publish(policy_path, work):
    require(os.environ.get("GITHUB_ACTIONS") == "true" and
            os.environ.get("GITHUB_REPOSITORY") == REPOSITORY and
            os.environ.get("GITHUB_REF") == "refs/heads/main" and
            os.environ.get("GITHUB_REF_PROTECTED") == "true" and
            os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch" and
            os.environ.get("GITHUB_WORKFLOW_REF") ==
            f"{REPOSITORY}/.github/workflows/release.yml@refs/heads/main" and
            os.environ.get("RELEASE_SIGNING_ENABLED") == "true",
            "Publishing requires the enabled protected-main GitHub Actions workflow")
    require(os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL") and
            os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN"),
            "GitHub Actions OIDC is unavailable")
    version = os.environ["RELEASE_VERSION"]
    source_commit = os.environ["SOURCE_COMMIT"]
    manifest_hash = os.environ["MANIFEST_SHA256"]
    names = archive_names(version)
    distribution_commit = os.environ["GITHUB_SHA"]
    require(valid_hash(distribution_commit, 40), "Invalid distribution workflow commit")
    require(run("git", "rev-parse", "HEAD").strip() == distribution_commit,
            "Checked-out workflow commit differs from the dispatch")
    require_release_source(distribution_commit)
    require_unused_tag(f"v{version}")
    policy = validate_policy(read_json(policy_path))
    tag = f"v{version}"
    require(not work.exists(), "Work directory already exists; use a fresh runner directory")
    work.mkdir()
    incoming = work / "incoming"
    executables = work / "executables"
    outgoing = work / "outgoing"
    for directory in (incoming, executables, outgoing):
        directory.mkdir()
    release = get_release(tag)
    require(release["tag_name"] == tag and
            release["target_commitish"] == distribution_commit,
            "Draft must target the exact reviewed distribution workflow commit")
    original = asset_snapshot(release)
    expected = {*names.values(), "release-manifest.json"}
    require(set(original) == expected, "Draft contains missing or unexpected assets")
    require(original["release-manifest.json"][1] <= 1024 * 1024 and
            all(original[name][1] <= MAX_ARCHIVE_BYTES for name in names.values()),
            "Staged asset exceeds size limit")
    download_assets(tag, incoming, expected)
    validate_handoff(incoming, policy, version, source_commit, manifest_hash, executables)
    cosign = install_cosign(policy, work)
    provenance = {
        "schema_version": 1,
        "product": "PixelBridge",
        "version": version,
        "source_repository": SOURCE_REPOSITORY,
        "source_commit": source_commit,
        "distribution_repository": REPOSITORY,
        "distribution_commit": distribution_commit,
        "manifest_sha256": manifest_hash,
        "workflow_identity": IDENTITY,
        "oidc_issuer": ISSUER,
        "workflow_run": (
            f"https://github.com/{REPOSITORY}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
            f"/attempts/{os.environ['GITHUB_RUN_ATTEMPT']}"
        ),
        "cosign_version": policy["cosign_version"],
        "cosign_linux_amd64_sha256": policy["cosign_linux_amd64_sha256"],
    }
    write_json(outgoing / "provenance.json", provenance)
    blobs = {name: incoming / name for name in expected}
    blobs["provenance.json"] = outgoing / "provenance.json"
    sums = "".join(f"{sha256(blobs[name])}  {name}\n" for name in sorted(blobs))
    (outgoing / "SHA256SUMS").write_text(sums, encoding="ascii")
    blobs["SHA256SUMS"] = outgoing / "SHA256SUMS"
    blobs.update({path.name: path for path in executables.iterdir()})
    for name, blob in sorted(blobs.items()):
        bundle = outgoing / f"{name}.sigstore.json"
        run(str(cosign), "sign-blob", "--yes", "--bundle", str(bundle), str(blob))
        verify_blob(cosign, blob, bundle)
    current = get_release(tag)
    require(current["id"] == release["id"] and
            current["target_commitish"] == distribution_commit and
            asset_snapshot(current) == original, "Draft changed during signing")
    outputs = sorted(outgoing.iterdir())
    run("gh", "release", "upload", tag, "--repo", REPOSITORY,
        *(str(path) for path in outputs))
    expected_final = expected | {path.name for path in outputs}
    current = get_release(tag)
    require(current["id"] == release["id"] and
            current["target_commitish"] == distribution_commit and
            set(asset_snapshot(current)) == expected_final and
            all(asset_snapshot(current).get(name) == snapshot
                for name, snapshot in original.items()), "Draft assets changed during upload")
    with tempfile.TemporaryDirectory(prefix="pixelbridge-verify-", dir=work) as temporary:
        downloaded = Path(temporary)
        download_assets(tag, downloaded, expected_final)
        for name in expected_final:
            local = incoming / name if name in expected else outgoing / name
            require(sha256(downloaded / name) == sha256(local),
                    f"Uploaded bytes differ: {name}")
        validate_handoff(downloaded, policy, version, source_commit, manifest_hash,
                         exact_assets=False)
        for name in blobs:
            blob = executables / name if name.endswith(".exe") else downloaded / name
            verify_blob(cosign, blob, downloaded / f"{name}.sigstore.json")
    require(asset_snapshot(get_release(tag)) == asset_snapshot(current),
            "Draft changed during final verification")
    require_release_source(distribution_commit)
    require_unused_tag(tag)
    notes = (
        f"PixelBridge {version}: Free, FreewithAds, Supporter and Pro production editions.\n\n"
        f"Source commit: `{source_commit}` (private application repository).\n"
        f"Distribution workflow commit: `{distribution_commit}`.\n"
        f"Signing run: {provenance['workflow_run']}\n\n"
        "Verify every download with its Sigstore bundle and the exact protected-main "
        "workflow identity. See https://github.com/QuasarLI/PixelBridge-Distribution/"
        "blob/main/docs/VERIFYING.md\n\n"
        "Sigstore signatures are not Windows Authenticode. Windows may display "
        "Unknown Publisher or SmartScreen warnings. Paid editions remain license-gated. "
        "All controller mappings are available in every edition."
    )
    notes_path = work / "release-notes.txt"
    notes_path.write_text(notes, encoding="utf-8")
    run("gh", "release", "edit", tag, "--repo", REPOSITORY,
        "--title", f"PixelBridge {version}", "--notes-file", str(notes_path),
        "--draft=false")
    published = gh_json(f"repos/{REPOSITORY}/releases/{release['id']}")
    require(published["draft"] is False and
            asset_snapshot(published) == asset_snapshot(current),
            "Published release state differs from verified draft; maintainer review required")
    tag_ref = gh_json(f"repos/{REPOSITORY}/git/ref/tags/{tag}")
    require(tag_ref["object"]["type"] == "commit" and
            tag_ref["object"]["sha"] == distribution_commit,
            "Published tag differs from reviewed workflow commit; maintainer review required")
    print(f"Published verified release: {published['html_url']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--policy", type=Path, required=True)
    validate.add_argument("--directory", type=Path, required=True)
    validate.add_argument("--version", required=True)
    validate.add_argument("--source-commit", required=True)
    validate.add_argument("--manifest-sha256", required=True)
    release = subparsers.add_parser("publish")
    release.add_argument("--policy", type=Path, required=True)
    release.add_argument("--work", type=Path, required=True)
    tool = subparsers.add_parser("check-tool")
    tool.add_argument("--policy", type=Path, required=True)
    tool.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate_handoff(args.directory, read_json(args.policy), args.version,
                             args.source_commit, args.manifest_sha256)
            print("Production handoff matches the reviewed policy and approved manifest.")
        elif args.command == "publish":
            publish(args.policy, args.work)
        else:
            args.directory.mkdir()
            cosign = install_cosign(read_json(args.policy), args.directory)
            for command, flags in (
                ("sign-blob", ("--yes", "--bundle")),
                ("verify-blob", ("--bundle", "--certificate-identity",
                                 "--certificate-oidc-issuer")),
            ):
                help_text = run(str(cosign), command, "--help")
                require(all(flag in help_text for flag in flags),
                        f"Pinned cosign does not support expected {command} interface")
            print("Pinned cosign checksum and command interfaces verified; no blobs signed.")
    except (ReleaseError, OSError, ValueError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as error:
        print(f"RELEASE REFUSED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
