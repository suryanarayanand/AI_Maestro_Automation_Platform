import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from web.services import repository_metadata_service as service


class RepositoryMetadataServiceTests(unittest.TestCase):
    def test_repository_url_rejects_embedded_credentials(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            service.validate_repository_url("https://token@example.com/repo.git")

    def test_save_token_uses_local_ignored_file(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "repository_credentials.local.json"
            completed = subprocess.CompletedProcess([], 0, "", "")
            with (
                patch.object(service, "CREDENTIAL_FILE", credential),
                patch.object(service, "_git", return_value="https://example.com/old.git"),
                patch.object(service, "sync_repository_metadata", return_value={}),
                patch.object(service.subprocess, "run", return_value=completed),
            ):
                service.save_repository_configuration(
                    "https://example.com/new.git", "secret-token"
                )

            self.assertEqual(
                json.loads(credential.read_text(encoding="utf-8"))["token"],
                "secret-token",
            )

    def test_pull_passes_token_in_environment_not_command(self):
        with tempfile.TemporaryDirectory() as directory:
            credential = Path(directory) / "repository_credentials.local.json"
            credential.write_text(json.dumps({"token": "secret-token"}), encoding="utf-8")
            completed = subprocess.CompletedProcess([], 0, "Already up to date.", "")
            with (
                patch.object(service, "CREDENTIAL_FILE", credential),
                patch.object(
                    service,
                    "_git",
                    side_effect=["https://example.com/repo.git", "main"],
                ),
                patch.object(service.subprocess, "run", return_value=completed) as run,
            ):
                service.pull_repository()

            command = run.call_args.args[0]
            environment = run.call_args.kwargs["env"]
            self.assertNotIn("secret-token", " ".join(command))
            self.assertEqual(
                environment["GIT_CONFIG_VALUE_0"], "Authorization: Bearer secret-token"
            )


if __name__ == "__main__":
    unittest.main()
