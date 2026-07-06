from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "fusion-flow.py"
SPEC = importlib.util.spec_from_file_location("fusion_flow", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
fusion_flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fusion_flow)


class LauncherTests(unittest.TestCase):
    def test_alias_contract_has_expected_models(self) -> None:
        aliases = fusion_flow.load_json(ROOT / "config" / "model-aliases.json")
        self.assertEqual(len(aliases), 9)
        self.assertIn("fusion-gpt-5.5-high", aliases)
        self.assertIn("fusion-sonnet-5-medium", aliases)
        self.assertIn("fusion-deepseek-v4-flash", aliases)

    def test_mask_secret(self) -> None:
        self.assertEqual(fusion_flow.mask_secret(""), "<none>")
        self.assertEqual(fusion_flow.mask_secret("abcd"), "****")
        self.assertEqual(fusion_flow.mask_secret("abcdefghijkl"), "abcd…ijkl")

    def test_gateway_url_validation(self) -> None:
        ok, detail = fusion_flow.gateway_reachable("not-a-url")
        self.assertFalse(ok)
        self.assertIn("invalid URL", detail)

    def test_config_round_trip_and_api_key_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            with patch.object(fusion_flow, "CONFIG_FILE", config_file):
                fusion_flow.save_config(
                    {
                        "base_url": "http://127.0.0.1:8080",
                        "auth_mode": "api_key",
                        "credential": "secret-value",
                    }
                )
                self.assertEqual(fusion_flow.load_config()["auth_mode"], "api_key")

                with patch.dict(
                    os.environ,
                    {
                        "FUSION_BASE_URL": "",
                        "FUSION_AUTH_MODE": "",
                        "FUSION_API_KEY": "",
                        "FUSION_AUTH_TOKEN": "",
                        "ANTHROPIC_API_KEY": "old",
                        "ANTHROPIC_AUTH_TOKEN": "old",
                    },
                    clear=False,
                ):
                    environment = fusion_flow.launch_environment()

                self.assertEqual(environment["ANTHROPIC_BASE_URL"], "http://127.0.0.1:8080")
                self.assertEqual(environment["ANTHROPIC_API_KEY"], "secret-value")
                self.assertNotIn("ANTHROPIC_AUTH_TOKEN", environment)

    def test_auth_token_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.json"
            with patch.object(fusion_flow, "CONFIG_FILE", config_file):
                fusion_flow.save_config(
                    {
                        "base_url": "http://127.0.0.1:8080",
                        "auth_mode": "auth_token",
                        "credential": "token-value",
                    }
                )
                with patch.dict(os.environ, {}, clear=True):
                    environment = fusion_flow.launch_environment()

                self.assertEqual(environment["ANTHROPIC_AUTH_TOKEN"], "token-value")
                self.assertNotIn("ANTHROPIC_API_KEY", environment)

    def test_unix_wrapper_resolves_installed_symlink(self) -> None:
        wrapper = (ROOT / "bin" / "fusion-flow").read_text(encoding="utf-8")
        self.assertIn("readlink", wrapper)
        self.assertIn("fusion-flow.py", wrapper)

    def test_windows_wrapper_targets_share_checkout(self) -> None:
        wrapper = (ROOT / "bin" / "fusion-flow.cmd").read_text(encoding="utf-8")
        self.assertIn(".local\\share\\fusion-workflow\\bin\\fusion-flow.py", wrapper)


if __name__ == "__main__":
    unittest.main()
