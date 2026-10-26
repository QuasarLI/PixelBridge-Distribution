import copy
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile


SPEC = importlib.util.spec_from_file_location(
    "release", Path(__file__).resolve().parents[1] / "scripts" / "release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.version = "1.2.0"
        self.commit = "a" * 40
        self.policy = {
            "schema_version": 1,
            "enabled": True,
            "candidate": {
                "version": self.version,
                "source_commit": self.commit,
                "manifest_sha256": "0" * 64,
            },
            "cosign_version": "v3.0.0",
            "cosign_linux_amd64_sha256": "b" * 64,
            "payload_files": {edition: ["PixelBridge.exe"] for edition in release.EDITIONS},
        }
        self.manifest = {
            "schema_version": 1,
            "product": "PixelBridge",
            "version": self.version,
            "source_repository": release.SOURCE_REPOSITORY,
            "source_commit": self.commit,
            "artifacts": [],
        }
        payload = b"synthetic validation fixture, not an executable or release artifact"
        for edition, name in sorted(release.archive_names(self.version).items(),
                                    key=lambda pair: pair[1]):
            path = self.directory / name
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("PixelBridge.exe", payload)
            self.manifest["artifacts"].append({
                "file": name,
                "edition": edition,
                "target": "win-x64",
                "size_bytes": path.stat().st_size,
                "sha256": release.sha256(path),
                "files": [{
                    "path": "PixelBridge.exe",
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                }],
            })
        self.save_manifest()

    def save_manifest(self):
        self.manifest_path = self.directory / "release-manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.manifest_hash = release.sha256(self.manifest_path)
        self.policy["candidate"]["manifest_sha256"] = self.manifest_hash

    def validate(self):
        return release.validate_handoff(self.directory, self.policy, self.version,
                                        self.commit, self.manifest_hash)

    def test_exact_handoff_is_accepted(self):
        self.assertEqual(self.validate(), self.manifest)

    def test_dispatch_inputs_must_match_pinned_candidate(self):
        for key, value in (("version", "1.2.1"), ("source_commit", "f" * 40),
                           ("manifest_sha256", "e" * 64)):
            with self.subTest(key=key):
                original = self.policy["candidate"][key]
                self.policy["candidate"][key] = value
                try:
                    with self.assertRaisesRegex(release.ReleaseError, "Inputs differ"):
                        self.validate()
                finally:
                    self.policy["candidate"][key] = original

    def test_candidate_fields_are_strictly_validated(self):
        self.policy["candidate"]["manifest_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(release.ReleaseError, "Invalid pinned release candidate"):
            self.validate()

    def test_disabled_policy_cannot_publish(self):
        self.policy["enabled"] = False
        with self.assertRaisesRegex(release.ReleaseError, "disabled"):
            self.validate()

    def test_disabled_policy_can_be_audited_without_enabling_publish(self):
        self.policy["enabled"] = False
        release.validate_handoff(
            self.directory, self.policy, self.version, self.commit, self.manifest_hash,
            require_enabled=False,
        )
        self.assertFalse(self.policy["enabled"])

    def test_extra_staged_asset_is_rejected(self):
        (self.directory / "PixelBridge-v1.2.0-Pro-LOCAL-TEST-win-x64.zip").write_bytes(b"")
        with self.assertRaisesRegex(release.ReleaseError, "exactly four"):
            self.validate()

    def test_archive_hash_is_not_enough_without_reviewed_payload(self):
        self.policy["payload_files"]["Free"] = ["PixelBridge.exe", "runtime.ps1"]
        with self.assertRaisesRegex(release.ReleaseError, "reviewed allowlist"):
            self.validate()

    def test_manifest_must_match_independently_approved_hash(self):
        self.manifest_path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(release.ReleaseError, "approved SHA256"):
            self.validate()

    def test_extra_manifest_field_is_rejected(self):
        self.manifest["local_path"] = "not public"
        self.save_manifest()
        with self.assertRaisesRegex(release.ReleaseError, "unexpected or missing"):
            self.validate()

    def test_source_commit_must_match_approval(self):
        self.manifest["source_commit"] = "c" * 40
        self.save_manifest()
        with self.assertRaisesRegex(release.ReleaseError, "source/version"):
            self.validate()

    def test_duplicate_edition_is_rejected(self):
        self.manifest["artifacts"][1] = copy.deepcopy(self.manifest["artifacts"][0])
        self.save_manifest()
        with self.assertRaisesRegex(release.ReleaseError, "exactly once"):
            self.validate()

    def test_hash_mismatch_is_rejected(self):
        path = self.directory / self.manifest["artifacts"][0]["file"]
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(release.ReleaseError, "ZIP differs"):
            self.validate()

    def test_payload_hash_is_checked(self):
        self.manifest["artifacts"][0]["files"][0]["sha256"] = "d" * 64
        self.save_manifest()
        with self.assertRaisesRegex(release.ReleaseError, "payload hash"):
            self.validate()

    def test_unsafe_windows_and_private_paths_are_rejected(self):
        for name in ("../escape", "A/../escape", "/absolute", "A\\escape",
                     "C:/escape", "A//B", "A/.git/config", "NUL.txt",
                     "a/COM1.cfg", "a.", "Pro-LOCAL-TEST.exe", "unlocked.exe",
                     "customer-key.json", "pairing.json", "config.pfx", "App.cs",
                     "Test.exe", "a/testing/file.txt", "local-settings.json"):
            with self.subTest(name=name), self.assertRaises(release.ReleaseError):
                release.safe_path(name)

    def test_controller_mapping_filename_is_not_blanket_blocked(self):
        self.assertEqual(release.safe_path("controller-profiles.json"),
                         "controller-profiles.json")

    def test_committed_payload_policy_preserves_all_edition_mappings(self):
        policy = release.read_json(Path(__file__).resolve().parents[1] / "release-policy.json")
        release.validate_policy(policy, require_enabled=False)
        common = policy["payload_files"]["Free"]
        self.assertEqual(len(common), 14)
        for edition in ("Supporter", "Pro"):
            self.assertEqual(policy["payload_files"][edition], common)
        self.assertEqual(
            policy["payload_files"]["FreewithAds"],
            sorted([*common, "Assets/AdGuard-728x90.png"]),
        )
        self.assertEqual(
            [path for path in common if path.startswith("Profiles/")],
            ["Profiles/Dreamcast.rmp", "Profiles/Genesis.rmp", "Profiles/N64.rmp",
             "Profiles/NES.rmp", "Profiles/PixelBridge-XInput.cfg", "Profiles/SNES.rmp"],
        )
        self.assertEqual(
            [path for path in common if path.endswith(".ps1")],
            ["PixelBridge-Backend.ps1", "PixelBridge-Performance.ps1"],
        )

    def test_case_colliding_policy_paths_are_rejected(self):
        self.policy["payload_files"]["Free"] = ["PixelBridge.exe", "pixelbridge.exe"]
        with self.assertRaisesRegex(release.ReleaseError, "case-unique"):
            self.validate()

    def test_duplicate_json_keys_are_rejected(self):
        self.manifest_path.write_text('{"schema_version":1,"schema_version":1}',
                                      encoding="utf-8")
        with self.assertRaisesRegex(release.ReleaseError, "Duplicate JSON"):
            release.read_json(self.manifest_path)

    def test_invalid_versions_and_hashes_are_rejected(self):
        for version in ("v1.2.0", "01.2.0", "1.2.0-LOCAL-TEST", "1.2.0/extra"):
            with self.subTest(version=version), self.assertRaises(release.ReleaseError):
                release.archive_names(version)
        self.assertFalse(release.valid_hash("A" * 64))

    def test_zip_extra_file_is_rejected_even_with_updated_archive_hash(self):
        artifact = self.manifest["artifacts"][0]
        path = self.directory / artifact["file"]
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("innocent-name.json", b"not reviewed")
        artifact["size_bytes"] = path.stat().st_size
        artifact["sha256"] = release.sha256(path)
        self.save_manifest()
        with self.assertRaisesRegex(release.ReleaseError, "unexpected ZIP entries"):
            self.validate()

    def test_zip_link_is_rejected(self):
        artifact = self.manifest["artifacts"][0]
        path = self.directory / artifact["file"]
        info = zipfile.ZipInfo("PixelBridge.exe")
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(info, b"target")
        artifact["size_bytes"] = path.stat().st_size
        artifact["sha256"] = release.sha256(path)
        self.save_manifest()
        with self.assertRaisesRegex(release.ReleaseError, "special files"):
            self.validate()

    def test_file_directory_collision_is_rejected(self):
        self.policy["payload_files"]["Free"] = ["PixelBridge.exe", "a", "a/b.txt"]
        with self.assertRaisesRegex(release.ReleaseError, "file/directory"):
            self.validate()

    def test_hidden_zip_prefix_or_suffix_is_rejected(self):
        artifact = self.manifest["artifacts"][0]
        path = self.directory / artifact["file"]
        original = path.read_bytes()
        for content in (b"hidden" + original, original + b"hidden"):
            with self.subTest(prefix=content.startswith(b"hidden")):
                path.write_bytes(content)
                artifact["size_bytes"] = len(content)
                artifact["sha256"] = release.sha256(path)
                self.save_manifest()
                with self.assertRaises(release.ReleaseError):
                    self.validate()

    def test_absent_pin_is_rejected(self):
        self.policy["cosign_linux_amd64_sha256"] = None
        with self.assertRaisesRegex(release.ReleaseError, "reviewed cosign"):
            self.validate()

    def test_existing_tag_is_never_reused(self):
        with mock.patch.object(release, "gh_json", return_value=[
            {"ref": "refs/tags/v1.2.0"}
        ]), self.assertRaisesRegex(release.ReleaseError, "never move or reuse"):
            release.require_unused_tag("v1.2.0")

    def test_tag_with_only_a_matching_prefix_is_not_an_existing_tag(self):
        with mock.patch.object(release, "gh_json", return_value=[
            {"ref": "refs/tags/v1.2.0-older"}
        ]):
            release.require_unused_tag("v1.2.0")

    def test_changed_or_unprotected_main_is_rejected(self):
        for protected, sha in ((False, self.commit), (True, "f" * 40)):
            with self.subTest(protected=protected), mock.patch.object(
                release, "gh_json", return_value={"protected": protected, "commit": {"sha": sha}}
            ), self.assertRaisesRegex(release.ReleaseError, "main moved"):
                release.require_release_source(self.commit)

    def test_production_publish_cannot_run_locally(self):
        with mock.patch.dict(release.os.environ, {}, clear=True), self.assertRaisesRegex(
            release.ReleaseError, "protected-main"
        ):
            release.publish(self.directory / "policy.json", self.directory / "work")

    def exercise_publish(self, fail_verification=False, mutate_draft=False):
        remote = {path.name: path.read_bytes() for path in self.directory.iterdir()}
        distribution_commit = "e" * 40
        staged = {
            "id": 42,
            "draft": True,
            "prerelease": False,
            "tag_name": "v1.2.0",
            "target_commitish": distribution_commit,
            "html_url": "https://github.com/QuasarLI/PixelBridge-Distribution/releases/tag/v1.2.0",
            "assets": [],
        }

        def add_asset(name, content):
            staged["assets"].append({
                "id": len(staged["assets"]) + 1,
                "name": name,
                "size": len(content),
                "updated_at": "fixed-test-timestamp",
                "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
            })

        for name, content in remote.items():
            add_asset(name, content)
        policy_path = self.directory / "policy.json"
        policy_path.write_text(json.dumps(self.policy), encoding="utf-8")
        commands = []
        verification_count = 0

        def fake_run(*args):
            nonlocal verification_count
            commands.append(args)
            if args[:3] == ("git", "rev-parse", "HEAD"):
                return distribution_commit
            if args[0] == "cosign":
                if args[1] == "sign-blob":
                    Path(args[args.index("--bundle") + 1]).write_bytes(b"synthetic bundle")
                    if mutate_draft:
                        staged["assets"][0]["updated_at"] = "changed-after-validation"
                elif args[1] == "verify-blob":
                    verification_count += 1
                    self.assertEqual(args[args.index("--certificate-identity") + 1],
                                     release.IDENTITY)
                    self.assertEqual(args[args.index("--certificate-oidc-issuer") + 1],
                                     release.ISSUER)
                    self.assertFalse(any("insecure" in value for value in args))
                    if fail_verification:
                        raise release.ReleaseError("synthetic signature rejection")
                return ""
            if args[:3] == ("gh", "release", "download"):
                name = args[args.index("--pattern") + 1]
                directory = Path(args[args.index("--dir") + 1])
                (directory / name).write_bytes(remote[name])
                return ""
            if args[:3] == ("gh", "release", "upload"):
                for value in args[6:]:
                    path = Path(value)
                    self.assertNotIn(path.name, remote)
                    remote[path.name] = path.read_bytes()
                    add_asset(path.name, remote[path.name])
                return ""
            if args[:3] == ("gh", "release", "edit"):
                self.assertEqual(verification_count, 22)
                self.assertIn("--draft=false", args)
                staged["draft"] = False
                return ""
            self.fail(f"Unexpected command: {args}")

        def fake_api(endpoint):
            if endpoint.endswith("/branches/main"):
                return {"protected": True, "commit": {"sha": distribution_commit}}
            if "/git/matching-refs/" in endpoint:
                return []
            if "/git/ref/" in endpoint:
                return {"object": {"type": "commit", "sha": distribution_commit}}
            if "/releases/" in endpoint:
                return copy.deepcopy(staged)
            self.fail(f"Unexpected API: {endpoint}")

        environment = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": release.REPOSITORY,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REF_PROTECTED": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_WORKFLOW_REF": (
                f"{release.REPOSITORY}/.github/workflows/release.yml@refs/heads/main"
            ),
            "RELEASE_SIGNING_ENABLED": "true",
            "ACTIONS_ID_TOKEN_REQUEST_URL": "not-a-real-oidc-url",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "synthetic-fixture",
            "RELEASE_VERSION": self.version,
            "SOURCE_COMMIT": self.commit,
            "MANIFEST_SHA256": self.manifest_hash,
            "GITHUB_SHA": distribution_commit,
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
        }
        with mock.patch.dict(release.os.environ, environment, clear=True), \
                mock.patch.object(release, "gh_json", side_effect=fake_api), \
                mock.patch.object(release, "run", side_effect=fake_run), \
                mock.patch.object(release, "install_cosign", return_value=Path("cosign")), \
                redirect_stdout(io.StringIO()):
            if fail_verification or mutate_draft:
                with self.assertRaises(release.ReleaseError):
                    release.publish(policy_path, self.directory / "work")
                self.assertTrue(staged["draft"])
                self.assertFalse(any(args[:3] == ("gh", "release", "edit")
                                     for args in commands))
            else:
                release.publish(policy_path, self.directory / "work")
                self.assertFalse(staged["draft"])
                self.assertEqual(len(remote), 18)
                self.assertEqual(len([name for name in remote
                                      if name.endswith(".sigstore.json")]), 11)
                self.assertFalse(any(name.endswith(".exe") for name in remote))

    def test_mocked_publish_rechecks_all_bytes_before_publishing(self):
        self.exercise_publish()

    def test_signature_failure_leaves_draft_unpublished(self):
        self.exercise_publish(fail_verification=True)

    def test_concurrent_draft_mutation_leaves_draft_unpublished(self):
        self.exercise_publish(mutate_draft=True)


if __name__ == "__main__":
    unittest.main()
