from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
WIZARD = ROOT / "bin" / "fusion_gateway_wizard.py"
ALIASES = ROOT / "config" / "model-aliases.json"
SPEC = importlib.util.spec_from_file_location("fusion_gateway_wizard", WIZARD)
assert SPEC is not None and SPEC.loader is not None
wizard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wizard)


class WizardAutopilotTests(unittest.TestCase):
    def aliases(self):
        return wizard.read_json(ALIASES)

    def test_generate_only_writes_all_routes_without_secrets_in_yaml(self) -> None:
        saved = {}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(wizard, "reachable", return_value=False), patch.dict(os.environ, {}, clear=True):
                result = wizard.run_gateway_wizard(
                    aliases=self.aliases(),
                    config_root=root,
                    save_fusion_config=lambda config: saved.update(config),
                    non_interactive=True,
                    skip_install=True,
                )

            self.assertEqual(result, 0)
            profile_dir = root / "gateway-profile"
            profile = wizard.read_json(profile_dir / "fusion-gateway-profile.json")
            config = (profile_dir / "litellm-config.yaml").read_text(encoding="utf-8")
            self.assertEqual(len(profile["routes"]), 9)
            self.assertEqual(config.count("  - model_name:"), 9)
            self.assertIn('reasoning_effort: "high"', config)
            self.assertIn('effort: "low"', config)
            self.assertIn('effort: "medium"', config)
            self.assertIn("os.environ/FUSION_GATEWAY_MASTER_KEY", config)
            self.assertNotIn(saved["credential"], config)
            self.assertEqual(saved["router"], "litellm")
            self.assertTrue((profile_dir / "provider-secrets.json").is_file())

    def test_ready_gateway_is_reused_without_generating_bundle(self) -> None:
        aliases = self.aliases()
        saved = {}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(wizard, "reachable", return_value=True), patch.object(
                wizard, "gateway_aliases", return_value=set(aliases)
            ):
                result = wizard.run_gateway_wizard(
                    aliases=aliases,
                    config_root=root,
                    save_fusion_config=lambda config: saved.update(config),
                    non_interactive=True,
                    skip_install=True,
                )

            self.assertEqual(result, 0)
            self.assertEqual(saved["router"], "external")
            self.assertFalse((root / "gateway-profile").exists())

    def test_busy_default_port_falls_back_to_free_local_port(self) -> None:
        required = {"one"}
        with patch.object(wizard, "reachable", side_effect=[True, False, False]), patch.object(
            wizard, "gateway_aliases", return_value=set()
        ):
            chosen, reused = wizard.choose_gateway_url("http://127.0.0.1:8080", required, "")
        self.assertFalse(reused)
        self.assertEqual(chosen, "http://127.0.0.1:4000")

    def test_model_matcher_prefers_provider_catalog_id(self) -> None:
        model, score = wizard.best_model_match("Sonnet 5", ["claude-haiku-5", "claude-sonnet-5-20260701"])
        self.assertEqual(model, "claude-sonnet-5-20260701")
        self.assertGreaterEqual(score, 0.60)


if __name__ == "__main__":
    unittest.main()
