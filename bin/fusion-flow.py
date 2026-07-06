#!/usr/bin/env python3
"""Fusion Workflow launcher and setup utility."""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
ALIASES_FILE = REPO_ROOT / "config" / "model-aliases.json"
PLUGIN_MANIFEST = REPO_ROOT / ".claude-plugin" / "plugin.json"
WIZARD_FILE = REPO_ROOT / "bin" / "fusion_gateway_wizard.py"
DEFAULT_BASE_URL = "http://127.0.0.1:8080"
MAIN_MODEL = "fusion-gpt-5.5-high"


def config_dir() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "fusion-workflow"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fusion-workflow"


CONFIG_FILE = config_dir() / "config.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")
    return value


def load_config() -> dict[str, Any]:
    return load_json(CONFIG_FILE)


def save_config(config: dict[str, Any]) -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    if os.name != "nt":
        temporary.chmod(0o600)
    temporary.replace(CONFIG_FILE)
    if os.name != "nt":
        CONFIG_FILE.chmod(0o600)


def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def mask_secret(secret: str) -> str:
    if not secret:
        return "<none>"
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}…{secret[-4:]}"


def resolve_runtime_config() -> dict[str, str]:
    config = load_config()
    base_url = os.environ.get("FUSION_BASE_URL") or str(config.get("base_url") or "").strip()
    auth_mode = os.environ.get("FUSION_AUTH_MODE") or str(config.get("auth_mode") or "none").strip()
    credential = (
        os.environ.get("FUSION_API_KEY")
        or os.environ.get("FUSION_AUTH_TOKEN")
        or str(config.get("credential") or "")
    )
    return {
        "base_url": base_url.rstrip("/"),
        "auth_mode": auth_mode,
        "credential": credential,
    }


def command_setup(args: argparse.Namespace) -> int:
    current = load_config()
    interactive = sys.stdin.isatty()

    if args.base_url:
        base_url = args.base_url.strip().rstrip("/")
    elif interactive:
        base_url = prompt("Anthropic-compatible gateway URL", str(current.get("base_url") or DEFAULT_BASE_URL)).rstrip("/")
    else:
        base_url = str(current.get("base_url") or DEFAULT_BASE_URL).rstrip("/")

    if args.auth_mode:
        auth_mode = args.auth_mode
    elif interactive:
        default_mode = str(current.get("auth_mode") or "api_key")
        while True:
            auth_mode = prompt("Authentication mode (api_key, auth_token, none)", default_mode).lower()
            if auth_mode in {"api_key", "auth_token", "none"}:
                break
            print("Choose api_key, auth_token, or none.")
    else:
        auth_mode = str(current.get("auth_mode") or "api_key")

    previous_credential = str(current.get("credential") or "")
    if auth_mode == "none":
        credential = ""
    elif args.token is not None:
        credential = args.token
    elif interactive:
        note = "leave blank to keep the existing value" if previous_credential else "leave blank if your gateway accepts no credential"
        entered = getpass.getpass(f"Gateway credential ({note}): ")
        credential = entered or previous_credential
    else:
        credential = previous_credential

    config = {
        **current,
        "base_url": base_url,
        "auth_mode": auth_mode,
        "credential": credential,
    }
    save_config(config)

    print(f"Saved Fusion config to {CONFIG_FILE}")
    print(f"Gateway: {base_url}")
    print(f"Auth: {auth_mode} ({mask_secret(credential)})")
    print("\nNext:")
    print("  1. Map the aliases shown by `fusion-flow models` in your gateway.")
    print("  2. Start the gateway.")
    print("  3. Run `fusion-flow doctor`.")
    print("  4. Run `fusion-flow` inside a git project.")
    return 0


def command_wizard(args: argparse.Namespace) -> int:
    if not WIZARD_FILE.is_file():
        print(f"Wizard file is missing: {WIZARD_FILE}", file=sys.stderr)
        return 1
    spec = importlib.util.spec_from_file_location("fusion_gateway_wizard", WIZARD_FILE)
    if spec is None or spec.loader is None:
        print(f"Could not load wizard module: {WIZARD_FILE}", file=sys.stderr)
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    aliases = load_json(ALIASES_FILE)
    return module.run_gateway_wizard(
        aliases=aliases,
        config_root=config_dir(),
        save_fusion_config=save_config,
        non_interactive=args.non_interactive,
        skip_install=args.skip_install,
        gateway_url=args.base_url or DEFAULT_BASE_URL,
    )


def check(label: str, ok: bool, detail: str) -> bool:
    mark = "OK" if ok else "FAIL"
    print(f"[{mark:4}] {label}: {detail}")
    return ok


def gateway_reachable(base_url: str) -> tuple[bool, str]:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False, "invalid URL; expected http:// or https://"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=1.5):
            return True, f"TCP connection to {parsed.hostname}:{port} succeeded"
    except OSError as exc:
        return False, f"cannot connect to {parsed.hostname}:{port} ({exc})"


def command_doctor(_: argparse.Namespace) -> int:
    failures = 0

    if not check("Python", sys.version_info >= (3, 9), sys.version.split()[0]):
        failures += 1

    claude = shutil.which("claude")
    if not check("Claude Code", bool(claude), claude or "not found on PATH"):
        failures += 1
    elif claude:
        try:
            result = subprocess.run([claude, "--version"], capture_output=True, text=True, timeout=5, check=False)
            version = (result.stdout or result.stderr).strip().splitlines()[0]
            check("Claude version", result.returncode == 0, version or "version command failed")
        except (OSError, subprocess.TimeoutExpired) as exc:
            check("Claude version", False, str(exc))

    git = shutil.which("git")
    if not check("Git", bool(git), git or "not found on PATH"):
        failures += 1

    if not check("Plugin manifest", PLUGIN_MANIFEST.is_file(), str(PLUGIN_MANIFEST)):
        failures += 1

    if not check("Gateway wizard", WIZARD_FILE.is_file(), str(WIZARD_FILE)):
        failures += 1

    try:
        aliases = load_json(ALIASES_FILE)
        aliases_ok = len(aliases) == 9
        if not check("Model aliases", aliases_ok, f"{len(aliases)} aliases loaded from {ALIASES_FILE}"):
            failures += 1
    except RuntimeError as exc:
        check("Model aliases", False, str(exc))
        failures += 1

    if not CONFIG_FILE.is_file():
        check("Fusion config", False, f"missing {CONFIG_FILE}; run `fusion-flow wizard`")
        failures += 1
    else:
        try:
            runtime = resolve_runtime_config()
            config = load_config()
            if not check("Fusion config", bool(runtime["base_url"]), str(CONFIG_FILE)):
                failures += 1
            profile_dir = str(config.get("gateway_profile_dir") or "")
            if profile_dir:
                check("Gateway profile", Path(profile_dir).is_dir(), profile_dir)
            if runtime["base_url"]:
                reachable, detail = gateway_reachable(runtime["base_url"])
                if not check("Gateway", reachable, detail):
                    failures += 1
            auth_detail = f"{runtime['auth_mode']} ({mask_secret(runtime['credential'])})"
            check("Gateway auth", runtime["auth_mode"] in {"api_key", "auth_token", "none"}, auth_detail)
        except RuntimeError as exc:
            check("Fusion config", False, str(exc))
            failures += 1

    if failures:
        print(f"\nDoctor found {failures} blocking problem(s).")
        return 1

    print("\nFusion is ready to launch. Alias routing is not probed because test requests would consume model quota.")
    return 0


def command_models(_: argparse.Namespace) -> int:
    aliases = load_json(ALIASES_FILE)
    width = max(len(name) for name in aliases)
    for alias, spec in aliases.items():
        provider = spec.get("provider", "")
        upstream = spec.get("upstream", "")
        mode = f" / {spec['mode']}" if spec.get("mode") else ""
        role = spec.get("role", "")
        print(f"{alias:<{width}}  ->  {provider}: {upstream}{mode}")
        print(f"{'':<{width}}      {role}")
    return 0


def command_config(_: argparse.Namespace) -> int:
    runtime = resolve_runtime_config()
    config = load_config()
    printable = {
        "config_file": str(CONFIG_FILE),
        "plugin_dir": str(REPO_ROOT),
        "main_model": MAIN_MODEL,
        "base_url": runtime["base_url"] or "<not configured>",
        "auth_mode": runtime["auth_mode"],
        "credential": mask_secret(runtime["credential"]),
        "gateway_profile_dir": config.get("gateway_profile_dir", "<not generated>"),
    }
    print(json.dumps(printable, indent=2))
    return 0


def launch_environment() -> dict[str, str]:
    runtime = resolve_runtime_config()
    if not runtime["base_url"]:
        raise RuntimeError(f"Fusion is not configured. Run `fusion-flow wizard` first. Expected config: {CONFIG_FILE}")

    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = runtime["base_url"]
    env["ANTHROPIC_API_BASE_URL"] = runtime["base_url"]
    env["CLAUDE_AGENT_API_BASE_URL"] = runtime["base_url"]

    env.pop("ANTHROPIC_API_KEY", None)
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    if runtime["auth_mode"] == "api_key" and runtime["credential"]:
        env["ANTHROPIC_API_KEY"] = runtime["credential"]
    elif runtime["auth_mode"] == "auth_token" and runtime["credential"]:
        env["ANTHROPIC_AUTH_TOKEN"] = runtime["credential"]

    return env


def command_launch(passthrough: list[str]) -> int:
    claude = shutil.which("claude")
    if not claude:
        print("Claude Code is not on PATH. Install it, then run `fusion-flow doctor`.", file=sys.stderr)
        return 1

    try:
        env = launch_environment()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    command = [
        claude,
        "--model",
        MAIN_MODEL,
        "--effort",
        "high",
        "--plugin-dir",
        str(REPO_ROOT),
        *passthrough,
    ]
    try:
        return subprocess.call(command, env=env)
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        print(f"Could not start Claude Code: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fusion-flow",
        description="Launch and configure the Fusion multi-model Claude Code workflow.",
    )
    subparsers = parser.add_subparsers(dest="command")

    wizard = subparsers.add_parser("wizard", help="configure Fusion and generate a gateway alias profile")
    wizard.add_argument("--base-url", help="local Anthropic-compatible gateway URL")
    wizard.add_argument("--non-interactive", action="store_true", help="accept defaults and write files without prompts")
    wizard.add_argument("--skip-install", action="store_true", help="skip gateway detection/install guidance")

    setup = subparsers.add_parser("setup", help="configure only the local gateway URL/auth")
    setup.add_argument("--base-url", help="Anthropic-compatible gateway URL")
    setup.add_argument("--auth-mode", choices=["api_key", "auth_token", "none"])
    setup.add_argument("--token", help="gateway credential; prefer the interactive prompt to avoid shell history")

    subparsers.add_parser("doctor", help="check local prerequisites and gateway reachability")
    subparsers.add_parser("models", help="print the required gateway model aliases")
    subparsers.add_parser("config", help="show sanitized active configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    commands = {"wizard", "setup", "doctor", "models", "config"}

    if argv and argv[0] in commands:
        parser = build_parser()
        args = parser.parse_args(argv)
        if args.command == "wizard":
            return command_wizard(args)
        if args.command == "setup":
            return command_setup(args)
        if args.command == "doctor":
            return command_doctor(args)
        if args.command == "models":
            return command_models(args)
        if args.command == "config":
            return command_config(args)
        parser.print_help()
        return 0

    if argv and argv[0] in {"-h", "--help"}:
        parser = build_parser()
        parser.print_help()
        print("\nAny other arguments are passed through to Claude Code. Running with no arguments launches Fusion.")
        return 0

    return command_launch(argv)


if __name__ == "__main__":
    raise SystemExit(main())
